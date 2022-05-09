import os
import re
import gspread
import _thread
import functions
import keyboards
from SQL import SQL
from time import sleep
from aiogram import types
from telegraph import upload
from copy import copy, deepcopy
from aiogram.utils import executor
from string import ascii_uppercase
from aiogram.dispatcher import Dispatcher
from datetime import datetime, timezone, timedelta
from functions import code, bold, time_now, html_secure
# =================================================================================================================
stamp1 = time_now()


def users_db_creation(table):
    db = SQL(db_path)
    spreadsheet = gspread.service_account('google.json').open('SportPostingDB')
    rows = spreadsheet.worksheet('users').get('A1:Z50000', major_dimension='ROWS')
    raw_columns = db.create_table(table, rows.pop(0), additional=True)
    rows_ids, columns = db.upload(table, raw_columns, rows)
    _zero_row = db.get_row(0)
    db.close()
    return _zero_row, ['id', *rows_ids], columns


functions.environmental_files()
os.makedirs('db', exist_ok=True)
tz = timezone(timedelta(hours=3))
admins, db_path, logging = [470292601, 396978030], 'db/database.db', []
Auth = functions.AuthCentre(ID_DEV=-1001312302092,
                            TOKEN=os.environ.get('TOKEN'),
                            ID_DUMP=os.environ.get('ID_DUMP'),
                            ID_LOGS=os.environ.get('ID_LOGS'),
                            ID_MEDIA=os.environ.get('ID_MEDIA'),
                            DEV_TOKEN=os.environ.get('DEV_TOKEN'),
                            ID_FORWARD=os.environ.get('ID_FORWARD'),
                            LOG_DELAY=5 if os.environ.get('local') else 120)
bot, dispatcher = Auth.async_bot, Dispatcher(Auth.async_bot)
zero_user, google_users_ids, users_columns = users_db_creation('users')
black_list = [os.environ.get(key, '') for key in ['ID_DUMP', 'ID_LOGS', 'ID_MEDIA', 'ID_FORWARD']]
black_list.extend(os.environ.get('black_list', '').split(' '))
# =================================================================================================================


async def clear_user(db: SQL, user: SQL.get_row):
    copied_user = deepcopy(user)
    update = {key: None for key in ['pic', 'title', 'sport', 'time',
                                    'teams', 'about', 'predict', 'rate', 'status']}
    copied_user.update(update)
    db.update('users', user['id'], update)
    return copied_user


def first_start(message):
    db, user = SQL(db_path), deepcopy(zero_user)
    _, name, username = Auth.logs.header(message['chat'].to_python())
    user.update({
        'name': name,
        'username': username,
        'id': message['chat']['id']})
    db.create_row(user)
    db.close()


async def editor(call, user, text, keyboard, log_text=None):
    global logging
    kwargs = {'log': log_text, 'call': call, 'text': text, 'user': user, 'keyboard': keyboard}
    response, log_text, update = await Auth.async_message(bot.edit_message_text, **kwargs)
    if log_text is not None:
        logging.append(log_text)
    if update:
        db = SQL(db_path)
        db.update('users', user['id'], update)
        db.close()
    return response


async def sender(message=None, user=None, text=None, log_text=None, **a_kwargs):
    global logging
    dump = True if 'Впервые' in str(log_text) else None
    task = a_kwargs['func'] if a_kwargs.get('func') else bot.send_message
    kwargs = {'log': log_text, 'text': text, 'user': user, 'message': message, **a_kwargs}
    response, log_text, update = await Auth.async_message(task, **kwargs)
    if log_text is not None:
        logging.append(log_text)
        if dump:
            head, _, _ = Auth.logs.header(Auth.get_me)
            await Auth.async_message(bot.send_message, id=Auth.logs.dump_chat_id, text=f'{head}{log_text}')
    if update:
        db = SQL(db_path)
        db.update('users', user['id'], update)
        db.close()
    return response


def iter_post(user: SQL.get_row, message_text: str = None):
    update = {}
    if user['status'] is not None and message_text:
        if user['status'] in ['sport', 'time', 'teams', 'predict', 'rate']:
            message_text = re.sub(r'\n+|\s+|_+', ' ', html_secure(message_text)).strip()
        if user['status'] == 'teams':
            message_text = re.sub('[-,.:;]', '—', message_text)
        if user['status'] == 'about':
            if message_text.lower() != 'нет':
                message_text = f'\n{message_text.strip()}'
                message_text = re.sub('\n+', '\n', message_text)
                message_text = re.sub('\n', '\n\n✅ ', html_secure(message_text)).strip()
            else:
                message_text = 'нет'

        user[user['status']] = message_text
        update = {'status': None, user['status']: user[user['status']]}

    text = f"{functions.html_link(user['pic'], '​​')}️" if user['pic'] else ''
    text += f"🔥{bold(user['title'])}🔥" if user['title'] else 'Создание нового поста'
    text += f"\n\n⚽ {bold(user['sport'])} ⚽" if user['sport'] else ''
    text += f"\n\n🕐 {bold(user['time'])}" if user['time'] else ''
    text += f"\n\n{bold(user['teams'])}" if user['teams'] else ''
    if user['about']:
        text += f"\n\n{bold(user['about'])}" if user['about'] != 'нет' else ''
    text += f"\n\n💬 {bold('Прогноз на матч:')} {bold(user['predict'])}" if user['predict'] else ''
    text += f"\n\n{bold('КФ:')} {bold(user['rate'])}" if user['rate'] else ''
    return user, text, update, re.sub('<.*?>', '', str(message_text))


def post(db: SQL, user: SQL.get_row, message_text: str = None):
    user, text, update, _ = iter_post(user, message_text)
    keys, action, action_alert = keyboards.Keys(), None, None
    keyboard = keys.post(user['pic']) if user['title'] else keys.bet()
    if user['status'] is not None and message_text:
        if len(re.sub('<.*?>', '', text)) > 4096:
            user[user['status']] = None
            user, text, update, _ = iter_post(user)
            action_alert = bold('⚠ Превышена максимальная длина поста')

    if user['title']:
        for key, action in [('sport', 'Какой спорт:'), ('time', 'Время игры:'), ('teams', 'Кто играет:'),
                            ('about', 'Описание:'), ('predict', 'Прогноз:'), ('rate', 'КФ:')]:
            action += f"\n\n{bold('нет')} — если нужно не выводить текст" if key == 'about' else ''
            if user[key] is None:
                update.update({'status': key}) if user['status'] != key else None
                break
        else:
            action, keyboard = None, keys.final(user['pic'])

    db.update('users', user['id'], update) if update else None
    action = f"{action_alert}\n\n{action}" if action_alert and action else action
    return text, action, keyboard


@dispatcher.chat_member_handler()
@dispatcher.my_chat_member_handler()
async def member_handler(message: types.ChatMember):
    global logging
    try:
        db = SQL(db_path)
        user = db.get_row(message['chat']['id'])
        log_text, update, greeting = Auth.logs.chat_member(message, user)
        if greeting and user is None:
            first_start(message)
        logging.append(log_text)
        db.update('users', message['chat']['id'], update) if update else None
        db.close()
    except IndexError and Exception:
        await Auth.dev.async_except(message)


@dispatcher.message_handler(content_types=functions.red_contents)
async def red_messages(message: types.Message):
    try:
        if str(message['chat']['id']) not in black_list:
            db = SQL(db_path)
            text, user, keyboard = None, db.get_row(message['chat']['id']), None
            if message['photo'] and user['admin'] == '🟢' and user['status'] == 'pic':
                try:
                    pic = await bot.download_file_by_id(message['photo'][len(message['photo']) - 1]['file_id'])
                    uploaded = upload.upload_file(pic)
                    user['pic'] = f"https://telegra.ph{uploaded[0]}"
                    db.update('users', user['id'], {'status': None, 'pic': user['pic']})
                    text, action, keyboard = post(db, user)
                except IndexError and Exception:
                    text, action = bold('⚠ Что-то пошло не так, попробуйте снова'), None

                if action:
                    await sender(message, user, text=text, keyboard=keyboard, log_text=None)
                    text, keyboard = action, None

            if user and message['migrate_to_chat_id']:
                db.update('users', user['id'], {'username': 'DISABLED_GROUP', 'reaction': '🅾️'})
            await sender(message, user, text=text, keyboard=keyboard, log_text=True)
            db.close()
    except IndexError and Exception:
        await Auth.dev.async_except(message)


@dispatcher.callback_query_handler()
async def callbacks(call):
    try:
        db = SQL(db_path)
        user = db.get_row(call['message']['chat']['id'])
        if user and user['admin'] == '🟢':
            edit_keys = call['message']['reply_markup']
            edit_text, log_text, send_text, send_keys = None, '', None, None

            if call['data'] == 'cancel':
                user = await clear_user(db, user)
                send_text = bold('Параметры сброшены')
                edit_text, _, edit_keys = post(db, user)

            elif call['data'].startswith('title'):
                user['title'] = re.sub('title_', '', call['data'], 1)
                db.update('users', user['id'], {'title': user['title']})
                edit_text, send_text, edit_keys = post(db, user)

            elif call['data'].startswith('picture'):
                if 'remove' not in call['data']:
                    send_text = 'Пришлите изображение:'
                    db.update('users', user['id'], {'status': 'pic'})
                else:
                    user['pic'] = None
                    db.update('users', user['id'], {'pic': None})
                    edit_text, send_text, edit_keys = post(db, user)

            elif call['data'] == 'publish':
                await clear_user(db, user)
                edit_text, send_text, edit_keys = post(db, user)
                if edit_keys == keyboards.Keys().final(user['pic']):
                    try:
                        channel_post = await sender(text=edit_text, id=os.environ['ID_CHANNEL'])
                        if channel_post['chat']['username']:
                            link = f"{functions.t_me}{channel_post['chat']['username']}"
                        else:
                            link = re.sub('-100', '', f"{functions.t_me}c/{channel_post['chat']['id']}")
                        send_text = f"{bold('Пост успешно опубликован')}\n\n" \
                                    f"Ссылка: {link}/{channel_post['message_id']}"
                        edit_keys = None
                    except IndexError and Exception:
                        send_text = bold('⚠ Что-то пошло не так, попробуйте снова')

            await editor(call, user, text=edit_text, keyboard=edit_keys, log_text=log_text)
            await sender(call['message'], user, send_text, keyboard=send_keys)
        db.close()
    except IndexError and Exception:
        await Auth.dev.async_except(call)


@dispatcher.message_handler()
async def repeat_all_messages(message: types.Message):
    try:
        db = SQL(db_path)
        user = db.get_row(message['chat']['id'])
        text, keyboard, is_first_start = None, None, None
        log_text = True if str(message['chat']['id']) not in black_list else None
        if user is None:
            first_start(message)
            is_first_start = True

        if message['text'].lower().startswith('/'):
            update, log_text = True, True
            if message['text'].lower().startswith('/start'):
                text = 'Добро пожаловать\n\nПост создается по команде /post'

            elif message['text'].lower().startswith('/time'):
                text = f"{bold(Auth.time(form='iso'))} ({code('GMT+3')})"

            elif message['text'].lower().startswith('/id'):
                if message['reply_to_message']:
                    replied_type = 'Человек'
                    reply = message['reply_to_message']['from']
                    _, name, username = Auth.logs.header(reply.to_python())
                    if reply['is_bot']:
                        replied_type = 'Я' if reply['username'] == Auth.username else 'Бот'
                    text = f"{name} [{bold(f'@{username}')}]\n" + \
                           f"ID: {code(reply['id'])}\n" \
                           f"Тип: {bold(replied_type)}"
                else:
                    text = f"Your ID: {code(message['from']['id'])}\n"
                    if message['chat']['id'] < 0:
                        text += f"Group ID: {code(message['chat']['id'])}"
            else:
                if db.is_user_admin(user['id']):
                    if message['text'].lower().startswith('/logs'):
                        text = Auth.logs.text()

                    elif message['text'].lower().startswith('/reboot'):
                        text, log_text = Auth.logs.reboot(dispatcher)

                    elif message['text'].lower().startswith('/post'):
                        update = False
                        text, action, keyboard = post(db, user)
                        if action:
                            await sender(message, user, text=text, keyboard=keyboard, log_text=None)
                            text, keyboard = action, None
            if update:
                db.update('users', user['id'], {'status': None}) if user['status'] else None
        else:
            if db.is_user_admin(user['id']):
                if user['status'] in ['sport', 'time', 'teams', 'about', 'predict', 'rate']:
                    text, action, keyboard = post(db, user, message['text'])
                    if action:
                        await sender(message, user, text=text, keyboard=keyboard, log_text=None)
                        text, keyboard = action, None

        log_text = ' [#Впервые]' if is_first_start else log_text
        await sender(message, user, text=text, keyboard=keyboard, log_text=log_text)
        db.close()
    except IndexError and Exception:
        await Auth.dev.async_except(message)


def logger():
    global logging
    while True:
        try:
            log = copy(logging)
            logging = []
            Auth.logs.send(log)
        except IndexError and Exception:
            Auth.dev.thread_except()


def auto_reboot():
    reboot = None
    while True:
        try:
            sleep(30)
            date = datetime.now(tz)
            if date.strftime('%H') == '01' and date.strftime('%M') == '59':
                reboot = True
                while date.strftime('%M') == '59':
                    sleep(1)
                    date = datetime.now(tz)
            if reboot:
                reboot = None
                text, _ = Auth.logs.reboot()
                Auth.dev.printer(text)
        except IndexError and Exception:
            Auth.dev.thread_except()


def google_update():
    global google_users_ids
    while True:
        try:
            sleep(2)
            db = SQL(db_path)
            records = db.get_updates()
            if len(records) > 0:
                client = gspread.service_account('google.json')
                worksheet = client.open('SportPostingDB').worksheet('users')
                for record in records:
                    del record['updates']
                    if str(record['id']) in google_users_ids:
                        text = 'обновлена'
                        row = google_users_ids.index(str(record['id'])) + 1
                    else:
                        text = 'добавлена'
                        row = len(google_users_ids) + 1
                        google_users_ids.append(str(record['id']))
                    google_row = f'A{row}:{ascii_uppercase[len(record)-1]}{row}'

                    try:
                        user_range = worksheet.range(google_row)
                    except IndexError and Exception as error:
                        if 'exceeds grid limits' in str(error):
                            worksheet.add_rows(1000)
                            user_range = worksheet.range(google_row)
                            sleep(5)
                        else:
                            raise error

                    for index, value, col_type in zip(range(len(record)), record.values(), users_columns):
                        value = Auth.time(value, form='iso', sep='_') if '<DATE>' in col_type else value
                        value = 'None' if value is None else value
                        user_range[index].value = value
                    worksheet.update_cells(user_range)
                    db.update('users', record['id'], {'updates': ['updates - 1']}, True)
                    Auth.dev.printer(f"Запись {text} {record['id']}")
                    sleep(1)
            db.close()
        except IndexError and Exception:
            Auth.dev.thread_except()


def start(stamp):
    try:
        if os.environ.get('local'):
            threads = [google_update, logger]
            Auth.dev.printer(f'Запуск бота локально за {time_now() - stamp} сек.')
        else:
            Auth.dev.start(stamp)
            threads = [google_update, auto_reboot, logger]
            Auth.dev.printer(f'Бот запущен за {time_now() - stamp} сек.')

        for thread_element in threads:
            _thread.start_new_thread(thread_element, ())
        executor.start_polling(dispatcher, allowed_updates=functions.allowed_updates)
    except IndexError and Exception:
        Auth.dev.thread_except()


if os.environ.get('local'):
    start(stamp1)
