import os
import re
import emoji
import base64
import gspread
import _thread
import functions
from SQL import SQL
from io import BytesIO
from time import sleep
from typing import Union
from aiogram import types
from telegraph import upload
from copy import copy, deepcopy
from keyboards import Keys, sport
from aiogram.utils import executor
from string import ascii_uppercase
from PIL.ImageFont import FreeTypeFont
from aiogram.dispatcher import Dispatcher
from PIL import Image, ImageFont, ImageDraw
from statistics import median as median_function
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
key_action = [('title', None), ('sport', None), ('time', 'Время игры:'),
              ('teams', 'Кто играет:'), ('about', 'Описание:'), ('predict', 'Прогноз:'), ('rate', 'КФ:')]
# =================================================================================================================


def font(size: int, weight: str = None):
    return ImageFont.truetype({}.get(weight, 'fonts/Lobster.ttf'), size)


def width(text: str, size: int, weight: str = None):
    emojis = emoji.emoji_list(text)
    emoji_size = size + (size * 0.4)
    text = emoji.replace_emoji(text, replace='') if emojis else text
    return FreeTypeFont.getbbox(font(size, weight), text)[2] + int(emoji_size + emoji_size * 0.11) * len(emojis)


def min_height(text: str, size: int, weight: str = None):
    letter_heights = [FreeTypeFont.getbbox(font(size, weight), i, anchor='lt')[3] for i in list(text)]
    descender_heights = [FreeTypeFont.getbbox(font(size, weight), i, anchor='ls')[3] for i in list(text)]
    result = [element1 - element2 for (element1, element2) in zip(letter_heights, descender_heights)]
    if emoji.emoji_list(text):
        return max(result)
    return median_function(result) if result else 0


def height(text: str, size: int, weight: str = None):
    emoji_size = size + (size * 0.4)
    response = int(emoji_size - emoji_size * 0.22) if emoji.emoji_list(text) else None
    if response is None:
        result = [FreeTypeFont.getbbox(font(size, weight), text, anchor=anchor)[3] for anchor in ['lt', 'ls']]
        response = result[0] - result[1]
    return response


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
    return user


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


def image(text: str, background: Union[Image.open, Image.new] = None,
          background_color: tuple[int, int, int] = (256, 256, 256),
          font_weight: str = 'condensed', text_align: str = 'center',
          font_size: int = 300, original_width: int = 1000, original_height: int = 1000,
          left_indent: int = 50, top_indent: int = 50, left_indent_2: int = 0, top_indent_2: int = 0):
    db = SQL('db/emoji.db')
    mask, spacing, response, coefficient, modal_height = None, 0, '', 0.6, 0
    original_width = background.getbbox()[2] if background and original_width == 1000 else original_width
    original_height = background.getbbox()[3] if background and original_height == 1000 else original_height
    original_scale = (original_width, original_height)
    original_height -= top_indent * 2 + top_indent_2
    original_width -= left_indent * 2 + left_indent_2
    font_size = font_size if font_size != 300 else original_width // 3
    background = copy(background) or Image.new('RGB', original_scale, background_color)
    while spacing < modal_height * coefficient or spacing == 0:
        mask = Image.new('RGBA', original_scale, (0, 0, 0, 0))
        skip, fonts, colors, layers, heights = False, [], [], [], []
        for line in text.strip().split('\n'):
            color, line_font, layer_array = (256, 256, 256), font_weight, []
            if line.startswith('**') and line.endswith('**'):
                line_font, line = 'bold', line.strip('**')
            if line.startswith('++') and line.endswith('++'):
                color, line = (47, 224, 39), line.strip('++')
            if line:
                for word in re.sub(r'\s+', ' ', line).strip().split(' '):
                    if width(word, font_size, line_font) > original_width:
                        skip = True
                        break
                    if width(' '.join(layer_array + [word]), font_size, line_font) > original_width:
                        heights.append(height(' '.join(layer_array), font_size, line_font))
                        colors.append(color), fonts.append(line_font), layers.append(' '.join(layer_array))
                        layer_array = [word]
                    else:
                        layer_array.append(word)
                else:
                    heights.append(height(' '.join(layer_array), font_size, line_font))
                    colors.append(color), fonts.append(line_font), layers.append(' '.join(layer_array))
            else:
                layers.append(''), heights.append(0), colors.append(color), fonts.append(line_font)

        if skip:
            font_size -= 1
            continue

        draw = copy(ImageDraw.Draw(mask))
        layers_count = len(layers) - 1 if len(layers) > 1 else 1
        full_height = heights[0] - min_height(layers[0], font_size, fonts[0])
        aligner, emoji_size, additional_height = 0, font_size + (font_size * 0.4), 0
        modal_height = max(heights) if emoji.emoji_list(text) else median_function(heights)
        full_height += sum([min_height(layers[i], font_size, fonts[i]) for i in range(0, len(layers))])
        spacing = (original_height - full_height) // layers_count
        if spacing > modal_height * coefficient:
            spacing = modal_height * coefficient
            aligner = (original_height - full_height - (spacing if len(layers) > 1 else 0) * layers_count) // 2
        for i in range(0, len(layers)):
            left = left_indent + left_indent_2
            emojis = [e['emoji'] for e in emoji.emoji_list(layers[i])]
            modded = (heights[i] - min_height(layers[i], font_size, fonts[i]))
            modded = modded if i != 0 or (i == 0 and layers_count == 0) else 0
            top = top_indent + top_indent_2 + aligner + additional_height - modded
            chunks = [re.sub('&#124;', '|', i) for i in emoji.replace_emoji(layers[i], replace='|').split('|')]
            left += (original_width - width(layers[i], font_size, fonts[i])) // 2 if text_align == 'center' else 0
            additional_height += heights[i] - modded + spacing

            for c in range(0, len(chunks)):
                chunk_width = width(chunks[c], font_size, fonts[i])
                emoji_scale = (left + chunk_width + int(emoji_size * 0.055), int(top))
                text_scale = (left, top + heights[i] - height(chunks[c], font_size, fonts[i]))
                draw.text(text_scale, chunks[c], colors[i], font(font_size, fonts[i]), anchor='lt')
                if c < len(emojis):
                    emoji_record = db.get_emoji(emojis[c])
                    if emoji_record:
                        emoji_image = BytesIO(base64.b64decode(emoji_record['data']))
                        foreground = Image.open(emoji_image).resize((int(emoji_size), int(emoji_size)), 3)
                    else:
                        foreground = Image.new('RGBA', (int(emoji_size), int(emoji_size)), (0, 0, 0, 1000))
                    try:
                        mask.paste(foreground, emoji_scale, foreground)
                    except IndexError and Exception:
                        mask.paste(foreground, emoji_scale)
                left += chunk_width + int(emoji_size + emoji_size * 0.11)
        font_size -= 1
    db.close()
    if mask:
        background.paste(mask, (0, 0), mask)
        background.save('image.jpg')
        doc = open('image.jpg', 'rb')
        response = f'https://telegra.ph{upload.upload_file(doc)[0]}'
        doc.close()
        os.remove('image.jpg')
    return response


def iter_post(user: SQL.get_row, message_text: str = None):
    text, update = '', {}
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

    if user['pic'] and user['pic'] != 'removed':
        text += f"{functions.html_link(user['pic'], '​​')}️"
    text += f"🔥{bold(user['title'])}🔥" if user['title'] else 'Создание нового поста'
    if user['sport']:
        text += f"\n\n{sport.get(user['sport'])} {bold(user['sport'])} {sport.get(user['sport'])}"
    text += f"\n\n🕐 {bold(user['time'])}" if user['time'] else ''
    text += f"\n\n{bold(user['teams'])}" if user['teams'] else ''
    if user['about']:
        text += f"\n\n{bold(user['about'])}" if user['about'] != 'нет' else ''
    text += f"\n\n💬 {bold('Прогноз на матч:')} {bold(user['predict'])}" if user['predict'] else ''
    text += f"\n\n{bold('КФ:')} {bold(user['rate'])}" if user['rate'] else ''
    return user, text, update, re.sub('<.*?>', '', str(message_text))


def post(db: SQL, user: SQL.get_row, message_text: str = None):
    keys, action, action_alert = Keys(), None, None
    user, text, update, _ = iter_post(user, message_text)
    keyboard = keys.post(user['pic'])
    for key, _ in key_action:
        if user[key] is None:
            if key in ['title', 'sport']:
                keyboard = keys.bet() if key == 'title' else keys.sport()
            break

    if user['status'] is not None and message_text:
        if len(re.sub('<.*?>', '', text)) > 4096:
            user[user['status']] = None
            user, text, update, _ = iter_post(user)
            action_alert = bold('⚠ Превышена максимальная длина поста')

    if user['title']:
        for key, action in key_action:
            if action:
                action += f"\n\n{bold('нет')} — если нужно не выводить текст" if key == 'about' else ''
            if user[key] is None:
                update.update({'status': key}) if action and user['status'] != key else None
                break
        else:
            if user['pic'] is None:
                background = Image.open('background.jpg')
                user['pic'] = image(f"{user['sport']}, начало в {user['time']}\n"
                                    f"матч {user['teams']}\n"
                                    f"++Прогноз: {user['predict']}++\n"
                                    f"КФ: {user['rate']}",
                                    original_width=background.getbbox()[2],
                                    original_height=background.getbbox()[3],
                                    background=background, font_weight='lobster',
                                    font_size=200, left_indent=200, top_indent=200)
                update.update({'pic': user['pic']})
                db.update('users', user['id'], update) if update else None
                user, text, update, _ = iter_post(user)
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

            elif call['data'].startswith('sport'):
                user['sport'] = re.sub('sport_', '', call['data'], 1)
                db.update('users', user['id'], {'sport': user['sport']})
                edit_text, send_text, edit_keys = post(db, user)

            elif call['data'].startswith('picture'):
                if 'remove' not in call['data']:
                    send_text = 'Пришлите изображение:'
                    db.update('users', user['id'], {'status': 'pic'})
                else:
                    user['pic'] = 'removed'
                    db.update('users', user['id'], {'pic': user['pic']})
                    edit_text, edit_keys = bold('Изображение удалено'), None
                    send_text, _, send_keys = post(db, user)

            elif call['data'] == 'back':
                send_text = bold('⚠ Что-то пошло не так, попробуйте снова')
                for key, action in reversed(key_action):
                    if user[key]:
                        user[key], user['pic'] = None, None
                        db.update('users', user['id'], {'pic': None, key: None})
                        edit_text, send_text, edit_keys = post(db, user)
                        break

            elif call['data'] == 'publish':
                await clear_user(db, user)
                edit_text, send_text, edit_keys = post(db, user)
                if edit_keys == Keys().final(user['pic']):
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
            is_first_start = True
            user = first_start(message)

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
