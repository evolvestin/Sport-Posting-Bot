import io
import os
import re
import sys
import time
import codecs
import base64
import aiogram
import asyncio
import inspect
import telebot
import heroku3
import _thread
import calendar
import traceback
import unicodedata
import concurrent.futures
from aiogram import types
from ast import literal_eval
from copy import copy, deepcopy
from unidecode import unidecode
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime, timezone, timedelta
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload

t_me = 'https://t.me/'
scope = ['https://www.googleapis.com/auth/drive']
html = {'{': '&#123;', '<': '&#60;', '}': '&#125;', '\'': '&#39;'}
standard_file_fields = 'files(id, name, parents, createdTime, modifiedTime)'
tags = {'bold': 'b', 'italic': 'i', 'text_link': 'a', 'underline': 'u', 'strikethrough': 's'}
week = {'Mon': 'Пн', 'Tue': 'Вт', 'Wed': 'Ср', 'Thu': 'Чт', 'Fri': 'Пт', 'Sat': 'Сб', 'Sun': 'Вс'}
signed = {'forward': 'Форварды', 'dump': 'Необработанные', 'media': 'Медиа-контент', 'dev': 'Главный тех. чат'}

media_contents = ['photo', 'document', 'animation', 'voice', 'audio', 'video', 'video_note',
                  'dice', 'poll', 'sticker', 'location', 'contact', 'new_chat_photo', 'game']

red_contents = [*media_contents, 'new_chat_title', 'delete_chat_photo', 'group_chat_created',
                'migrate_to_chat_id', 'migrate_from_chat_id', 'pinned_message']

allowed_updates = ['callback_query', 'channel_post', 'chat_member', 'chosen_inline_result', 'poll',
                   'chosen_inline_result', 'edited_channel_post', 'edited_message', 'inline_query',
                   'message', 'my_chat_member', 'poll_answer', 'pre_checkout_query', 'shipping_query']

patterns = {'major': 'The (read|write) operation timed out|Backend Error'
                     '|is currently unavailable.|returned "Internal Error"',
            'retry': r'Retry in (\d+) seconds|Please try again in (\d+) seconds.|'
                     r'"Too Many Requests: retry after (\d+)"',
            'block': 'initiate conversation with a user|user is deactivated|Have no rights'
                     '|The group has been migrated|bot was kicked from the supergroup chat'
                     '|bot was blocked by the user|Chat not found|bot was kicked from the group chat',
            'minor': 'Message to forward not found|Message can&#39;t be forwarded|Message_id_invalid'
                     '|Read timed out.|ServerDisconnectedError|EOF occurred in violation of protocol'
                     '|Connection aborted|Connection reset by peer|Failed to establish a new connection'}


def bold(text):
    return f'<b>{text}</b>'


def italic(text):
    return f'<i>{text}</i>'


def strike(text):
    return f'<s>{text}</s>'


def under(text):
    return f'<u>{text}</u>'


def code(text):
    return f'<code>{text}</code>'


def make_dict(value):
    return literal_eval(str(value))


def html_link(link, text):
    return f'<a href="{link}">{text}</a>'


def divide(array, sep=10000):
    return [array[i:i + sep] for i in range(0, len(array), sep)]


def time_now(delta=3):
    return int(datetime.now(timezone(timedelta(hours=delta))).timestamp())


def html_secure(text, reverse=None):
    for pattern, value in html.items():
        text = re.sub(pattern, value, str(text)) if reverse is None else re.sub(value, pattern, str(text))
    return text


def concurrent_functions(array):
    array = [array] if type(array) != list else array
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as future_executor:
        futures = [future_executor.submit(future) for future in array]
        for future in concurrent.futures.as_completed(futures):
            print(future.result())


def chunks(array, separate):
    separated = []
    d, r = divmod(len(array), separate)
    for i in range(separate):
        sep = (d+1)*(i if i < r else r) + d*(0 if i < r else i - r)
        separated.append(array[sep:sep+(d+1 if i < r else d)])
    return separated


def stamper(date, delta=0, pattern=None):
    try:
        if pattern is None:
            stamp = int(datetime.fromisoformat(str(date)).timestamp())
        else:
            stamp = int(calendar.timegm(time.strptime(str(date), pattern)))
    except IndexError and Exception:
        stamp = None
    return stamp - delta * 60 * 60 if stamp else None


def environmental_files(python=None):
    created_files, local_files = [], os.listdir('.')
    for key in os.environ.keys():
        key = key.lower()
        if key.endswith('.json'):
            created_files.append(key)
            if key not in local_files:
                with open(key, 'w') as file:
                    file.write(os.environ.get(key))
        if python and key.endswith('.py'):
            with codecs.open(key, 'w', 'utf-8') as file:
                file.write(base64.b64decode(os.environ.get(key)).decode('utf-8'))
    return created_files


def iter_entities(text=None, raw_entities=None):
    text_list = []
    if text:
        raw_entities = raw_entities if type(raw_entities) == list else []
        position, entities, used_offsets, text_list = 0, [], [], list(text)

        for entity in raw_entities:
            if entity.get('type') == 'text_mention':
                entity.update({'type': 'text_link', 'url': f"tg://user?id={entity['user']['id']}"})
            entities.append(entity)

        for char in text_list:
            if char in html:
                text_list[position] = html[char]
            else:
                length = len(char.encode('utf-16-le')) // 2
                while length > 1:
                    text_list.insert(position+1, '')
                    length -= 1
            position += 1

        for entity in reversed(entities):
            space = entity['offset'] + entity['length']
            end_index = len(text_list) - 1 if space >= len(text_list) else space - 1
            if entity['type'] != 'mention':
                tag = tags[entity['type']] if entity['type'] in tags else 'code'
                if space not in used_offsets or entity['type'] == 'text_link':
                    used_offsets.append(space)
                    if text_list[end_index] == '\n':
                        text_list[end_index] = f'</{tag}>\n'
                    else:
                        text_list[end_index] += f'</{tag}>'
                    tag = f"a href='{entity['url']}'" if entity['type'] == 'text_link' else tag
                    text_list[entity['offset']] = f"<{tag}>{text_list[entity['offset']]}"
    return ''.join(text_list)


def chats_to_human(counter, delay, current):
    array, day = [], 24 * 60 * 60
    r_seconds = (999990 - current + counter * 999990) * delay
    data = {'year': 365 * day, 'month': 30 * day, 'day': day, 'hour': 60 * 60, 'minute': 60}

    for key in data:
        value = int(r_seconds / data[key])
        r_seconds -= value * data[key]
        data[key] = value

    pack = [(data['year'], 'год', 'года', 'лет'), (data['month'], 'месяц', 'месяца', 'месяцев'),
            (data['day'], 'день', 'дня', 'дней'), (data['hour'], 'час', 'часа', 'часов')]
    if all(data[key] == 0 for key in ['year', 'month', 'day', 'hour']):
        pack.extend([(data['minute'], 'мин.', 'мин.', 'мин.'), (r_seconds, 'сек.', 'сек.', 'сек.')])

    for value, text1, text2, text3 in pack:
        if value:
            ending = text1 if value in [1, 21] else text3
            ending = text2 if value in [2, 3, 4, 22, 23, 24] else ending
            array.append(f'{value} {ending}')

    last = f' и {array.pop(-1)}' if len(array) > 1 else ''
    text = f"{', '.join(array)}{last}".rstrip('.')
    return f'{text}.' if text else ''


class GoogleDrive:
    def __init__(self, path):
        credentials = service_account.Credentials.from_service_account_file(path, scopes=scope)
        self.client = build('drive', 'v3', credentials=credentials)

    @staticmethod
    def modify_time(file):
        for key in ['modifiedTime', 'createdTime']:
            if file.get(key):
                file[key] = stamper(re.sub('Z', '', file[key]))
        return file

    def delete_file(self, file_id):
        self.client.files().delete(fileId=file_id).execute()

    def add_file_to_folder(self, file_id, folder_id):
        self.client.files().update(fileId=file_id, addParents=folder_id).execute()

    def file(self, file_id):
        fields = 'id, name, parents, createdTime, modifiedTime'
        result = self.client.files().get(fileId=file_id, fields=fields).execute()
        return self.modify_time(result)

    def get_permissions(self, file_id):
        fields = 'permissions(id, emailAddress, role)'
        response = self.client.permissions().list(fileId=file_id, fields=fields).execute()
        return response['permissions']

    def update_file(self, file_id, file_path, description=''):
        file_metadata = {'description': description}
        media_body = MediaFileUpload(file_path, resumable=True)
        return self.client.files().update(fileId=file_id, media_body=media_body, body=file_metadata).execute()

    def create_folder(self, name, folder_id):
        file_metadata = {'name': name, 'parents': [folder_id], 'mimeType': 'application/vnd.google-apps.folder'}
        result = self.client.files().create(body=file_metadata, fields='id, name, createdTime').execute()
        return self.modify_time(result)

    def move_file_to_folder(self, file_id, folder_id, remove_from_previous_folder=True):
        file = self.client.files().get(fileId=file_id, fields='parents').execute()
        previous_parents = ",".join(file.get('parents')) if remove_from_previous_folder else ''
        self.client.files().update(fileId=file_id, addParents=folder_id, removeParents=previous_parents).execute()

    def create_file(self, file_path, folder_id, same_file_name=True):
        if same_file_name is True:
            same_file_name = re.sub('(.*)/', '', file_path)
        media_body = MediaFileUpload(file_path, resumable=True)
        file_metadata = {'name': same_file_name, 'parents': [folder_id]}
        return self.client.files().create(body=file_metadata, media_body=media_body, fields='id').execute()

    def files(self, fields=standard_file_fields, only_folders=None, name_startswith=None, parents=None):
        queries = []
        queries.append(f"'{parents}' in parents") if parents else None
        queries.append(f"name contains '{name_startswith}'") if name_startswith else None
        queries.append("mimeType='application/vnd.google-apps.folder'") if only_folders else None
        result = self.client.files().list(q=' and '.join(queries), pageSize=1000, fields=fields).execute()
        return [self.modify_time(file) for file in result['files']]

    def get_file_by_name(self, file_name, fields=standard_file_fields):
        response = None
        drive_response = self.client.files().list(pageSize=1000, fields=fields).execute()
        for file in drive_response['files']:
            if file_name == file['name']:
                response = self.modify_time(file)
                break
        return response

    def download_file(self, file_id, file_path):
        done, file = False, io.FileIO(file_path, 'wb')
        downloader = MediaIoBaseDownload(file, self.client.files().get_media(fileId=file_id))
        while done is False:
            try:
                status, done = downloader.next_chunk()
            except IndexError and Exception:
                done = False


class AuthCentre:
    def __init__(self, **kwargs):
        # BOTS
        token = kwargs.get('TOKEN')
        if token is None:
            token = kwargs.get('DEV_TOKEN')
        self.LogChats.async_message = self.async_message
        self.DevChat.time = self.LogChats.time = self.time
        self.bot = self.LogChats.main_bot = telebot.TeleBot(token)
        self.DevChat.message = self.LogChats.message = self.message
        self.async_bot = self.LogChats.async_bot = aiogram.Bot(token)
        self.get_me = self.LogChats.get_me = self.bot.get_me().to_dict()
        self.username = self.DevChat.username = self.LogChats.username = self.get_me.get('username')

        # LogChats VARIABLES
        if kwargs.get('LOG_TOKEN') and kwargs.get('LOG_TOKEN') != token:
            self.LogChats.bot = telebot.TeleBot(kwargs['LOG_TOKEN'])
        else:
            self.LogChats.bot = self.bot

        # DevChat VARIABLES
        self.DevChat.chat_id = self.LogChats.dev_chat_id = kwargs.get('ID_DEV')
        if kwargs.get('DEV_TOKEN') and kwargs.get('DEV_TOKEN') != token:
            self.DevChat.bot = telebot.TeleBot(kwargs['DEV_TOKEN'])
        else:
            self.DevChat.bot = self.bot

        # VARIABLES
        if type(kwargs.get('GMT')) == int:
            self.delta = kwargs['GMT']
        elif type(kwargs.get('GMT')) == str:
            self.delta = int(re.sub(r'[^0-9-]', '', kwargs['GMT']))
        else:
            self.delta = 3

        self.dev = self.LogChats.dev = self.DevChat()
        self.logs = self.LogChats(**kwargs)

    def time(self, stamp=None, form=None, sep=None, tag=None, seconds=True):
        tz = timezone(timedelta(hours=self.delta))
        stamp = int(datetime.now(tz).timestamp()) if stamp is None else stamp
        date = datetime.fromtimestamp(stamp, tz)
        sep = '.' if form is None else sep
        if form != 'iso':
            response = f"{date.strftime('%d')}-{date.strftime('%m')}-{date.strftime('%Y')}"
            response = re.sub('-', sep, response) if sep else response
            if form != 'date':
                response += f" {date.strftime('%H')}:{date.strftime('%M')}"
                response += f":{date.strftime('%S')}" if seconds else ''
            response = f"{week[date.strftime('%a')]} {response}" if form is None else response
        else:
            response = re.sub(r'\+.*', '', date.isoformat(sep=sep if sep else ' '))
        return tag(response) if tag else response

    def message(self, **kwargs):
        edited = None
        message = None
        bot = self.dev.bot
        chat_id = self.dev.chat_id
        if kwargs.get('id'):
            bot = self.bot
            chat_id = kwargs['id']
            if chat_id in self.logs.chat_ids:
                bot = self.logs.bot

        if kwargs.get('old_message') and kwargs.get('text'):
            try:
                if kwargs.get('replace') is None:
                    entities = kwargs['old_message'].json.get('entities')
                    kwargs['text'] = iter_entities(kwargs['old_message'].text, entities) + kwargs['text']
                edited = bot.edit_message_text(kwargs['text'], kwargs['old_message'].chat.id,
                                               message_id=kwargs['old_message'].message_id,
                                               disable_web_page_preview=True, parse_mode='HTML')
            except IndexError and Exception:
                kwargs['text'] += italic('\nСтарое сообщение недоступно')

        if kwargs.get('document'):
            bot.send_document(chat_id, kwargs['document'], caption=kwargs.get('caption'), parse_mode='HTML')

        if kwargs.get('text') and edited is None:
            message = bot.send_message(chat_id, kwargs['text'], disable_web_page_preview=True, parse_mode='HTML')
        return edited if edited else message

    async def async_message(self, task, **kwargs):
        user, hard, response, task_name = {}, True, None, 'unknown'
        log_text = '' if kwargs.get('log') is True else kwargs.get('log')
        target_id = kwargs['id'] if kwargs.get('id') else self.logs.media_chat_id
        try:
            task_name = task.__name__
            if task_name in ['send_video_note', 'send_sticker']:
                response = await task(target_id, kwargs['file_id'], reply_to_message_id=kwargs.get('reply'))

            elif task_name == 'forward_message':
                message = kwargs['message']
                response = await task(target_id, message['chat']['id'], message['message_id'])

            elif task_name in ['send_audio', 'send_photo', 'send_video', 'send_voice', 'send_document']:
                caption = kwargs['text'] if kwargs.get('text') else kwargs.get('caption')
                file = types.InputFile(kwargs['path']) if kwargs.get('path') else kwargs['file_id']
                response = await task(target_id, file, parse_mode='HTML',
                                      caption=caption, reply_to_message_id=kwargs.get('reply'))

            elif task_name == 'send_message':
                if kwargs.get('message'):
                    target_id = kwargs['message']['chat']['id']
                if kwargs.get('text'):
                    response = await task(target_id, kwargs['text'],
                                          reply_markup=kwargs.get('keyboard'), parse_mode='HTML',
                                          reply_to_message_id=kwargs.get('reply'), disable_web_page_preview=False)

            elif task_name == 'edit_message_text':
                if kwargs.get('call'):
                    modified, hard = None, None
                    message = kwargs['call']['message']
                    message['date'] = time_now(self.delta)
                    message['from'] = kwargs['call']['from']
                    log_text = 'Нажал' if log_text is None else log_text
                    try:
                        await self.async_bot.answer_callback_query(kwargs['call']['id'], text=kwargs.get('answer'))
                    except IndexError and Exception:
                        pass

                    if kwargs.get('text'):
                        modified = html_secure(re.sub('<.*?>', '', kwargs['text']), reverse=True).strip()
                    try:
                        if message['text'] == modified or kwargs.get('text') is None:
                            if kwargs.get('keyboard') != message['reply_markup']:
                                task = self.async_bot.edit_message_reply_markup
                                await task(message['chat']['id'], message['message_id'],
                                           reply_markup=kwargs.get('keyboard'))
                        else:
                            await task(kwargs['text'], message['chat']['id'],
                                       message['message_id'], parse_mode='HTML',
                                       reply_markup=kwargs.get('keyboard'), disable_web_page_preview=True)
                    except IndexError and Exception as error:
                        error_text = ''
                        log_text += ', но получил #timeout'
                        try:
                            answer_task = self.async_bot.answer_callback_query
                            await answer_task(kwargs['call']['id'], text=kwargs.get('timeout'))
                        except IndexError and Exception as answer_error:
                            error_text += f'\nAnswer error: {answer_error}'
                        if re.search('Query is too old', str(error)) is None:
                            self.dev.executive(f"{error}{error_text}\n{kwargs['call']}")

                    log_text += f" #{kwargs['call']['data'].upper()}"

        except IndexError and Exception as error:
            search_block = re.search(patterns['block'], str(error))
            search_retry = re.search(r'Retry in (\d+) seconds', str(error))
            if search_retry:
                kwargs['log'] = None
                await asyncio.sleep(int(search_retry.group(1)) + 1)
                response, log_text, user = await self.async_message(task, **kwargs)
            elif search_block:
                user.update({'reaction': '🅾️'})
                if log_text is not None:
                    log_text += bold(' [Не отправлено]')
            else:
                error_text = ''
                for key in kwargs:
                    if key in ['call', 'message', 'keyboard'] and kwargs[key] is not None:
                        kwargs[key] = kwargs[key].to_python()

                if kwargs.get('text'):
                    error_text = f"\nlen(re.sub(<.*?>, text)) = " \
                                 f"{len(re.sub('<.*?>', '', str(kwargs['text'])))}" \
                                 f"\nlen(text) = {len(str(kwargs['text']))}\ntext = {kwargs['text']}"
                self.dev.executive(f'Not delivered {task_name.upper()} to: {target_id}\n'
                                   f'Short error: {error}{error_text}\nKeys: {kwargs}')

        if log_text is not None:
            message = kwargs['call']['message'] if kwargs.get('call') else kwargs['message']
            data, data_update = await self.logs.data(message, kwargs.get('user'), hard)
            user.update(data_update) if data_update else None
            log_text = data + log_text
        return response, log_text, user

    # ------------------------------------------------------------------------------------------ LOG CHATS BEGIN
    class LogChats:
        def __init__(self, **kwargs):
            self.chat_ids = []
            self.bot = self.bot
            self.dev = self.dev
            self.time = self.time
            self.target_chat = None
            self.get_me = self.get_me
            self.message = self.message
            self.last_record_id = 999990
            self.username = self.username
            self.main_bot = self.main_bot
            self.async_bot = self.async_bot
            self.arrows = code('&#62;&#62;')
            self.async_message = self.async_message
            self.others = {self.dev.chat_id: self.get_chat(self.dev.bot, self.dev.chat_id)}

            if type(kwargs.get('ID_LOGS')) == int:
                self.chat_ids.append(kwargs['ID_LOGS'])
            elif type(kwargs.get('ID_LOGS')) == list:
                self.chat_ids = [int(chat_id) for chat_id in kwargs['ID_LOGS']]
            elif type(kwargs.get('ID_LOGS')) == str:
                chat_string = re.sub('\n', ' ', kwargs['ID_LOGS'])
                self.chat_ids = [int(chat_id) for chat_id in chat_string.split(' ')]

            if type(kwargs.get('ID_MEDIA')) in [str, int]:
                self.media_chat_id = int(kwargs['ID_MEDIA'])
            else:
                chat_id = None
                if len(self.chat_ids) > 0:
                    chat_id = self.chat_ids[0]
                self.media_chat_id = chat_id

            if type(kwargs.get('ID_FORWARD')) in [str, int]:
                self.forward_chat_id = int(kwargs['ID_FORWARD'])
            else:
                self.forward_chat_id = self.media_chat_id

            if type(kwargs.get('ID_DUMP')) in [str, int]:
                self.dump_chat_id = int(kwargs['ID_DUMP'])
            else:
                self.dump_chat_id = self.forward_chat_id

            if type(kwargs.get('LOG_DELAY')) == int:
                self.delay = kwargs['LOG_DELAY']
            elif type(kwargs.get('LOG_DELAY')) == str:
                self.delay = int(re.sub(r'\D', '', kwargs['LOG_DELAY']))
            elif len(self.chat_ids) == 0:
                self.delay = 0
            else:
                self.delay = 15

            self.chats = self.get_chats(self.chat_ids, log=True)
            for chat_id in self.chats:
                if 'FILLED' not in self.chats[chat_id]['title']:
                    self.target_chat = deepcopy(self.chats[chat_id])
                    if self.dump_chat_id in self.chat_ids:
                        self.dump_chat_id = chat_id
                    if self.media_chat_id in self.chat_ids:
                        self.media_chat_id = chat_id
                    if self.forward_chat_id in self.chat_ids:
                        self.forward_chat_id = chat_id
                    break

            self.others.update(self.get_chats([self.media_chat_id, self.forward_chat_id, self.dump_chat_id]))

        @staticmethod
        def channel_link(channel_message):
            if channel_message['chat']['username']:
                link = f"{t_me}{channel_message['chat']['username']}"
            else:
                link = re.sub('-100', '', f"{t_me}c/{channel_message['chat']['id']}")
            return f"{link}/{channel_message['message_id']}"

        @staticmethod
        def get_chat(bot, chat_id):
            keys = ['sign', 'type', 'title', 'description', 'invite_link', 'start_time', 'end_time']
            value = {key: None for key in keys}
            try:
                signs = []
                start_time, end_time = None, None
                chat = bot.get_chat(int(chat_id))
                if chat.description:
                    search_end = re.search(r'До: (.*)', chat.description)
                    search_start = re.search(r'От: (.*)', chat.description)
                    end_time = search_end.group(1) if search_end else None
                    start_time = search_start.group(1) if search_start else None
                for sign in ['dev', 'forward', 'media', 'dump']:
                    signs.append(sign) if sign in str(chat.title).lower() else None
                value.update({
                    'id': chat.id,
                    'type': chat.type,
                    'title': chat.title,
                    'end_time': stamper(end_time),
                    'invite_link': chat.invite_link,
                    'start_time': stamper(start_time),
                    'sign': '/'.join(signs) if signs else None,
                    'description': html_secure(chat.description)})
                if chat.type == 'private':
                    value.update({'title': chat.first_name, 'invite_link': f'tg://user?id={chat.id}'})
                value['title'] = html_secure(value['title'])
            except IndexError and Exception:
                value.update({'id': chat_id, 'title': 'FILLED'})
            return value

        def get_chats(self, chat_ids, log=None):
            chats = {}
            if type(chat_ids) == str:
                chat_ids = [int(chat_id) for chat_id in chat_ids.split(' ')]
            for chat_id in chat_ids:
                chats[chat_id] = self.get_chat(self.bot if log else self.main_bot, chat_id)
            return chats

        def header(self, sign, date=None, text=None):
            text = text if text else ''
            title = f"{sign['title']} " if sign.get('title') else ''
            chat_id = f" {code(sign['id'])}" if sign.get('id') else ''
            username = sign['username'] if sign.get('username') else ''
            response = f'{self.time(date, tag=code)} {text}' if date else ''
            last_name = f"{sign['last_name']} " if sign.get('last_name') else ''
            first_name = f"{sign['first_name']} " if sign.get('first_name') else ''

            name = html_secure(first_name + last_name + title).strip()
            response += f"{name} [@{username}]{chat_id}:"
            return response, name, sign.get('username')

        def head(self, message, user):
            space, update = '', {}
            head, name, username = self.header(message['chat'].to_python(), message.to_python().get('date'))
            if user and user['username'] != 'DISABLED_GROUP':
                if name != user['name'] or username != user['username']:
                    update = {'name': name, 'username': username}
                if user['reaction'] == '🅾️':
                    update.update({'reaction': '♿'})
            if message['chat']['id'] < 0 and message['from']:
                space = ' ' * 5
                head_text, _, _ = self.header(message['from'].to_python())
                head += f'\n{space}👤 {head_text}'
            return head, name, username, space, update

        def reboot(self, dispatcher=None):
            def heroku(_delay, connection):
                time.sleep(4)
                if dispatcher:
                    dispatcher.stop_polling()
                    time.sleep(_delay+1)
                for app in connection.apps():
                    for dyno in app.dynos():
                        dyno.restart()

            if os.environ.get('api'):
                postfix = 'секунд'
                delay = self.delay+5
                if delay < 10 or 20 < delay < 110 or delay > 120:
                    postfix += 'у' if str(delay)[-1] in ['1'] else ''
                    postfix += 'ы' if str(delay)[-1] in ['2', '3', '4'] else ''

                connect = heroku3.from_key(os.environ['api'])
                _thread.start_new_thread(heroku, (self.delay, connect,))
                text, log_text = f'✅ Перезапуск через {delay} {postfix}.', '[Успешно]'
            else:
                text, log_text = '❌ Переменная окружения не установлена.', '[Неудачно]'
            return bold(text), f' {bold(log_text)}'

        def text(self):
            def links(array, title_one='', title_many='', sep='\n'):
                text, count, enumerated = '', 0, []
                if len(array) > 0:
                    text = f'\n{bold(title_many if len(array) > 1 else title_one)}:\n'
                    for _chat in array:
                        count += 1
                        count_text = f'{count}. ' if len(array) > 1 and sep == '\n' else ''
                        enumerated.append(count_text + html_link(_chat['invite_link'], _chat['sign']))
                return text + sep.join(enumerated) + '\n' if text else ''

            response, d_chats = '', []
            p_channels, r_channels, d_channels = [], [], []
            for chat in deepcopy(self.others).values():
                if chat['sign']:
                    last = ''
                    signs = chat['sign'].split('/')
                    for i in range(len(signs)):
                        if signs[i] in signed:
                            signs[i] = signed[signs[i]]
                    if len(signs) > 1:
                        last = f' и {signs.pop(-1).lower()}'
                    chat['sign'] = f"{', '.join(signs).capitalize()}{last}"
                else:
                    chat['sign'] = chat['title']
                if chat['type'] == 'channel':
                    d_channels.append(chat)
                else:
                    d_chats.append(chat)

            for chat in deepcopy(self.chats).values():
                if 'RESERVED' not in chat['title']:
                    start_time, end_time = '', ''
                    if chat['start_time']:
                        start_time = f"От {self.time(chat['start_time'], form='date', sep='.')}"
                        end_time = ' до настоящего времени'
                    if chat['end_time']:
                        end_time = f" до {self.time(chat['end_time'], form='date', sep='.')}"
                    chat['sign'] = start_time + end_time
                    if chat['sign']:
                        p_channels.append(chat)
                    else:
                        chat['title'] += 'RESERVED'

                if 'RESERVED' in chat['title']:
                    chat['sign'] = 'канал'
                    r_channels.append(chat)

            response += links(d_chats, 'Чат', 'Чаты') + links(d_channels, 'Доп. канал', 'Доп. каналы')
            response += links(p_channels, 'Канал со всеми логами', 'Каналы со всеми логами, по периодам')

            if len(self.chat_ids) > 0:
                if len(r_channels) > 0:
                    if len(r_channels) == 1:
                        link = html_link(r_channels[0]['invite_link'], 'канал')
                        response += f"\n{bold(f'Зарезервирован один {link} под логи')}\n"
                    else:
                        ending = 'а' if len(r_channels) in [2, 3, 4] else 'ов'
                        title = f'Зарезервировано {len(r_channels)} канал{ending} под логи'
                        response += links(r_channels, title_many=title, sep=',  ')
                else:
                    response += f"\n{bold(f'Каналов под логи не зарезервировано')}\n"
                reserved_text = chats_to_human(len(r_channels), self.delay, self.last_record_id)
                if reserved_text:
                    response += italic(f'Этого хватит еще на {reserved_text}')
                else:
                    response += italic('Канал с логами будет переполняться.')
            return response

        def send(self, array):
            if array:
                send = []
                log_text = ''
                for text in array:
                    if len(log_text + text) <= 4096:
                        log_text += text
                    else:
                        send.append(log_text)
                        log_text = text
                if log_text:
                    send.append(log_text)
                for text in send:
                    if len(text) > 4096 and len(re.sub('<.*?>', '', text)) > 4096:
                        split = re.split(f'({self.arrows})', text)
                        description = f" {bold('Большое сообщение')}: #split"
                        modified_text = re.sub(r'\n\s+', '\n', split.pop(-1))
                        for s_text in [''.join(split) + description, modified_text]:
                            log_message = self.message(id=self.target_chat['id'], text=s_text)
                    else:
                        log_message = self.message(id=self.target_chat['id'], text=text)
                    self.last_record_id = log_message.id if log_message else self.last_record_id

                    if log_message and log_message.id >= 999990:
                        new_chat = None
                        for chat_id in self.chats:
                            if 'FILLED' not in self.chats[chat_id]['title'] and \
                                    chat_id != self.target_chat['id']:
                                new_chat = deepcopy(self.chats[chat_id])
                                break

                        if new_chat:
                            self.target_chat['end_time'] = log_message.date
                            end_time = self.time(log_message.date, form='iso')
                            if 'FILLED' not in self.target_chat['title']:
                                self.target_chat['title'] = f"FILLED {self.target_chat['title']}"
                            if self.target_chat['description']:
                                self.target_chat['description'] = \
                                    re.sub('настоящего времени', end_time, self.target_chat['description'])
                            else:
                                self.target_chat['description'] = \
                                    f'Логи за период:\n\n' \
                                    f"От: {self.target_chat['start_time']}\n" \
                                    f'До: {end_time}'

                            new_chat.update({
                                'start_time': stamper(end_time),
                                'title': re.sub('RESERVED', '', new_chat['title']).strip(),
                                'description': f'Логи за период:\n\nОт: {end_time}\nДо: настоящего времени'})

                            try:
                                self.bot.set_chat_title(self.target_chat['id'], self.target_chat['title'])
                                self.bot.set_chat_description(self.target_chat['id'],
                                                              self.target_chat['description'])

                                self.bot.set_chat_title(new_chat['id'], new_chat['title'])
                                self.bot.set_chat_description(new_chat['id'], new_chat['description'])

                                self.chats[self.target_chat['id']] = deepcopy(self.target_chat)
                                self.chats[new_chat['id']] = deepcopy(new_chat)

                                dev_text = f"{bold('Константное изменение:')}\n" \
                                           f"Новый чат логов: {new_chat.get('invite_link')}\n" \
                                           f"Старый: {self.target_chat.get('invite_link')}"

                                self.target_chat = deepcopy(new_chat)
                                if self.dump_chat_id in self.chat_ids:
                                    self.dump_chat_id = new_chat['id']
                                if self.media_chat_id in self.chat_ids:
                                    self.media_chat_id = new_chat['id']
                                if self.forward_chat_id in self.chat_ids:
                                    self.forward_chat_id = new_chat['id']
                                self.dev.send(dev_text, tag=None)
                                self.others.update(self.get_chats([self.media_chat_id,
                                                                   self.forward_chat_id,
                                                                   self.dump_chat_id]))
                            except IndexError and Exception as error:
                                old_chat_id = self.target_chat.get('id')
                                new_chat_id = new_chat.get('id')
                                error_text = f'Error switching log chats: \n' \
                                             f'OLD CHAT ID: {old_chat_id}\n' \
                                             f'OLD CHAT: {self.target_chat}\n\n' \
                                             f'NEW CHAT ID: {new_chat_id}\n' \
                                             f'NEW CHAT: {new_chat}' \
                                             f'Error: {error}'
                                self.dev.executive(error_text)
            time.sleep(self.delay)

        def chat_member(self, message, user):
            for key in ['old', 'new']:
                message[f'{key}_chat_member']['until_date'] = time_now()
            action = {'tag': '', 'text': '', 'tag_type': 'bot', 'user_type': 'бота'}
            text, name, username, space, update = self.head(message, user)
            greeting, text = None, f'\n{text}\n{space}{self.arrows} '
            status = {'old': message['old_chat_member']['status'],
                      'new': message['new_chat_member']['status']}
            member = message['new_chat_member']['user']

            if member['is_bot'] is False:
                action.update({'tag_type': 'user', 'user_type': 'пользователя'})

            if member['id'] != message['from']['id']:
                if status['old'] in ['left', 'kicked']:
                    if message['chat']['id'] < 0:
                        action['tag'] = 'added'
                        if member['username'] == self.username:
                            greeting = True
                            update['reaction'] = '♿'

                        action['text'] = 'Добавил %s'
                        if status['new'] == 'left':
                            action['tag'] = 'changed'
                            action['text'] = 'Разрешил вход %s'

                        elif status['new'] == 'kicked':
                            action['tag'] = 'changed'
                            action['text'] = 'Запретил вход %s'

                        elif status['new'] == 'administrator':
                            action['text'] += ' как админа'

                        if message['chat']['type'] == 'channel':
                            action['text'] += ' в канал'
                        else:
                            action['text'] += ' в чат'
                    else:
                        action['text'], action['tag'] = 'Разблокировал %s', 'unblocked'
                        if member['username'] == self.username:
                            update['reaction'] = '♿'
                else:
                    if message['chat']['id'] < 0:
                        action['tag'] = 'kicked'
                        if message['chat']['type'] == 'channel':
                            action['text'] = 'Удалил %s с канала'
                            if member['username'] == self.username:
                                update['reaction'] = '🅾️'
                        else:
                            if status['new'] in ['left', 'kicked']:
                                action['text'] = 'Удалил %s из чата'
                                if member['username'] == self.username:
                                    update['reaction'] = '🅾️'
                            else:
                                action['tag'] = 'changed'
                                if status['new'] == 'administrator':
                                    if status['old'] == 'administrator':
                                        action['text'] = 'Изменил %s как админа'
                                    else:
                                        action['text'] = 'Назначил %s админом'

                                elif status['old'] == 'restricted' and status['new'] != 'restricted':
                                    action['text'] = 'Снял ограничения %s'

                                elif status['new'] == 'restricted':
                                    action['text'] = 'Ограничил %s'
                                    if member['username'] == self.username \
                                            and message['new_chat_member']['can_send_messages'] is False:
                                        update['reaction'] = '🔕'

                                else:
                                    action['text'] = 'Забрал роль админа у %s'
                    else:
                        action['text'], action['tag'] = 'Заблокировал %s', 'block'
                        if member['username'] == self.username:
                            update['reaction'] = '🅾️'

                member_text, _, _ = self.header(member.to_python())
                emoji = '🤖' if action['tag_type'] == 'bot' else '👤'
                action['member'] = f"\n{space}{' ' * 5}{emoji} {member_text[:-1]}"
                if user and user['reaction'] == '🔕' and member['username'] == self.username \
                        and message['new_chat_member']['can_send_messages'] is True:
                    update['reaction'] = '♿'
            else:
                chat_type = 'канал' if message['chat']['type'] == 'channel' else 'чат'
                if status['old'] in ['left', 'kicked']:
                    action['text'], action['tag'] = f'Зашел в {chat_type} по ссылке', 'added'
                else:
                    action['text'], action['tag'] = f'Вышел из {chat_type}а', 'left'

            if '%' in action['text']:
                action['text'] %= action['user_type']
            text += f"{bold(action['text'])} #{action['tag_type']}_{action['tag']}"
            text += ' #me' if member['username'] == self.username else ''
            text += action['member'] if action.get('member') else ''
            return text, update if update and user else None, greeting

        async def data(self, message, user=None, hard=True):
            text = ''
            head, name, username, space, update = self.head(message, user)

            if message['forward_from'] or message['forward_from_chat'] or message['forward_sender_name']:
                f_space = space
                space += ' ' * 5
                task = self.async_bot.forward_message
                f_message, _, _ = await self.async_message(task, id=self.forward_chat_id, message=message)

                if message['forward_sender_name']:
                    forward = {'id': None, 'first_name': message['forward_sender_name']}
                else:
                    if message['forward_from']:
                        forward = message['forward_from'].to_python()
                    else:
                        forward = message['forward_from_chat'].to_python()

                head_text, _, _ = self.header(forward, message.to_python().get('forward_date'), f'\n{space}')
                link = html_link(self.channel_link(f_message), 'Форвард')
                head += f'\n{f_space}{self.arrows} {link} от {head_text}'

            head = f'\n{head}\n{space}{self.arrows} '
            space += ' ' * 6

            if hard:
                if message['text'] or message['caption']:
                    if message['text']:
                        entities = message.to_python().get('entities')
                        text += iter_entities(message['text'], entities)
                    else:
                        entities = message.to_python().get('caption_entities')
                        text += '\n' + iter_entities(message['caption'], entities)
                    text = re.sub('\n', f'\n{space}', text)

                if message['pinned_message']:
                    text += bold('Закрепил сообщение #pinned_message:')
                    pinned, _ = await self.data(message['pinned_message'], user)
                    text += re.sub('\n', f'\n{space}', pinned)

                if message['new_chat_title']:
                    text += f"{bold('Изменил название чата')} #new_chat_title"

                elif message['delete_chat_photo']:
                    text += f"{bold('Удалил аватар чата')} #chat_photo_deleted"

                elif message['group_chat_created']:
                    text += f"{bold('Создал чат')} #chat_created"

                elif message['migrate_to_chat_id']:
                    text += f"{bold('Чат деактивирован:')} #chat_upgrade\n" \
                            f"{space}Новый ID: {code(message['migrate_to_chat_id'])}"

                elif message['migrate_from_chat_id']:
                    text += f"{bold('Чат стал супергруппой:')} #chat_upgraded\n" \
                            f"{space}Старый ID: {code(message['migrate_from_chat_id'])}"

            for message_type in media_contents:
                if message[message_type]:
                    media_text = ''
                    task = self.async_bot.forward_message
                    caption = re.sub(f'\n{space}', '\n', text)

                    if message['forward_from_chat']:
                        from_ch = message['forward_from_chat']
                        c_message = {'message_id': message['forward_from_message_id'],
                                     'chat': {'id': from_ch['id'], 'username': from_ch['username']}}
                        media_text += f'\n{space}{self.channel_link(c_message)}'

                    if message_type == 'photo':
                        task = self.async_bot.send_photo
                        doc_type = f"{bold('фото')} #{message_type}"
                        file_id = message['photo'][len(message['photo']) - 1]['file_id']
                        keys = {'file_id': file_id, 'caption': caption}

                    elif message_type == 'document':
                        task = self.async_bot.send_document
                        doc_type = f"{bold('документа')} #{message_type}"
                        if message['animation']:
                            continue
                        keys = {'file_id': message['document']['file_id'], 'caption': caption}

                    elif message_type == 'animation':
                        task = self.async_bot.send_document
                        doc_type = bold('анимации') + f' #gif #{message_type}'
                        keys = {'file_id': message['animation']['file_id'], 'caption': caption}

                    elif message_type == 'voice':
                        task = self.async_bot.send_voice
                        doc_type = f"{bold('голосового сообщения')} #{message_type}"
                        keys = {'file_id': message['voice']['file_id'], 'caption': caption}

                    elif message_type == 'audio':
                        task = self.async_bot.send_audio
                        doc_type = f"{bold('аудио')} #{message_type}"
                        keys = {'file_id': message['audio']['file_id'], 'caption': caption}

                    elif message_type == 'video':
                        task = self.async_bot.send_video
                        doc_type = f"{bold('видео')} #{message_type}"
                        keys = {'file_id': message['video']['file_id'], 'caption': caption}

                    elif message_type == 'video_note':
                        task = self.async_bot.send_video_note
                        keys = {'file_id': message['video_note']['file_id']}
                        doc_type = f"{bold('видео-сообщения')} #{message_type}"

                    elif message_type == 'dice':
                        keys = {'message': message}
                        doc_type = f"{bold('игральной кости')} #{message_type}"

                    elif message_type == 'poll':
                        doc_type = 'голосования'
                        keys = {'message': message}
                        if message['poll']['type'] == 'quiz':
                            doc_type = 'викторины'
                        doc_type = f'{bold(doc_type)} #{message_type}'

                    elif message_type == 'sticker':
                        task = self.async_bot.send_sticker
                        doc_type = f"{bold('стикера')} #{message_type}"
                        keys = {'file_id': message['sticker']['file_id']}
                        media_text += f"\n{space}{t_me}addstickers/{message['sticker']['set_name']}"

                    elif message_type == 'location':
                        keys = {'message': message}
                        doc_type = f"{bold('адреса')} #{message_type}"

                    elif message_type == 'contact':
                        keys = {'message': message}
                        contact = message['contact']
                        doc_type = f"{bold('контакта')} #{message_type}"
                        if contact['user_id']:
                            media_text += f"\n{space}ID пользователя: {code(contact['user_id'])}"

                    elif message_type == 'new_chat_photo':
                        task = self.async_bot.send_photo
                        head_text, _, _ = self.header(message['chat'].to_python())
                        doc_type = f"нового {bold('аватара')} чата #{message_type}"
                        file_id = message['new_chat_photo'][len(message['new_chat_photo']) - 1]['file_id']
                        keys = {'file_id': file_id, 'caption': f"Новый аватар в чате:\n{head_text[:-1]}"}

                    elif message_type == 'game':
                        keys = {'message': message}
                        doc_type = f"{bold('игры')} #{message_type}"

                    else:
                        keys = {'message': message}
                        doc_type = f"{bold('Unknown')} #{message_type} #Unknown"

                    reply_head, _, _ = self.header(self.get_me)
                    media, _, _ = await self.async_message(task, **keys)
                    if media:
                        text = f"Прислал #media в виде {doc_type}" \
                               f"{' с подписью:' if message['caption'] else ''}{text}" \
                               f"{space + media_text if media_text else ''}" \
                               f"\n{space}{self.channel_link(media)}"
                        await self.async_message(self.async_bot.send_message,
                                                 text=reply_head + head + text, reply=media['message_id'])
            return head + text, update if update else None
    # ------------------------------------------------------------------------------------------ LOG CHATS END

    # ------------------------------------------------------------------------------------------ DEV CHAT BEGIN
    class DevChat:
        def __init__(self):
            self.bot = self.bot
            self.time = self.time
            self.message = self.message
            self.chat_id = self.chat_id
            self.username = self.username
            self.app_name = copy(self.username)
            self.bot_link = f'{t_me}{self.username}'
            self.host = 'server' if os.environ.get('server') else 'local'

            if os.environ.get('api'):
                for app in heroku3.from_key(os.environ['api']).apps():
                    self.app_name = re.sub('-first|-second', '', app.name, 1)
                    self.host = 'One' if app.name.endswith('first') else self.host
                    self.host = 'Two' if app.name.endswith('second') else self.host

        def header(self, text=None):
            text = f':\n{text}' if text else ''
            return f'{html_link(self.bot_link, bold(self.app_name))} ({code(self.host)}){text}'

        def send(self, text, tag=code):
            return self.message(text=self.header(tag(html_secure(text)) if tag else text))

        def printer(self, text):
            prefix = self.time() if self.host in ['server', 'local'] else ''
            print(f'{prefix} [{_thread.get_ident()}] {text}'.strip())

        def start(self, stamp, text=None):
            text = f'{self.time(stamp, tag=code)}\n' \
                   f'{self.time(tag=code)}\n' \
                   f"{text if text else ''}"
            return self.message(text=self.header(text))

        # -------------------------------------------------------------------------------- DEV EXECUTIVE
        def send_except(self, title='', error=None, message=None):
            len_title = len(re.sub('<.*?>', '', title))
            error = str(error) if error else ''
            len_text = len_title + len(error)
            caption, message_text = None, ''
            if message is not None:
                for character in str(message):
                    replaced = unidecode(str(character))
                    if replaced != '':
                        message_text += replaced
                    else:
                        try:
                            message_text += f'[{unicodedata.name(character)}]'
                        except ValueError:
                            message_text += '[???]'

            if message_text:
                caption = f'{title}{code(error)}' if 0 < len_text <= 1024 else None
                file_name = f"error_report_{re.sub(':', '-', self.time(form='iso', sep='_'))}.json"
                with open(file_name, 'w') as file:
                    file.write(message_text)
                with open(file_name, 'rb') as file:
                    self.message(document=file, caption=caption)
                os.remove(file_name)

            if len_text > 0 and (message_text == '' or caption is None):
                for text in divide(error, 4096 - len_title):
                    self.message(text=f'{title}{code(text)}')
                    title = ''

        def executive(self, message):
            exc_type, exc_value, exc_traceback = sys.exc_info()
            error_raw = traceback.format_exception(exc_type, exc_value, exc_traceback)
            error = ''.join([html_secure(e) for e in error_raw])
            search_retry = re.search(patterns['retry'], error)
            minor_fails = re.search(patterns['minor'], error)
            major_fails = re.search(patterns['major'], error)
            self.printer(f'Ошибка {error_raw[-1]}')
            function_name = 'module'

            retry = int(search_retry.group(1)) + 5 if search_retry else 100
            if minor_fails or major_fails:
                message, error = None, None
                retry = 5 if minor_fails else 99
            for thread in inspect.stack():
                if thread[3] not in ['executive', 'thread_except', 'async_except']:
                    function_name = html_secure(re.sub('[<>]', '', thread[3]))
                    break
            head = f"{self.header()}.{bold(f'{function_name}()')}"
            self.send_except(f'Вылет {head}\n', error, message)
            return 0 if message else retry, f'Работает {head}'

        def thread_except(self, message=None):
            retry, text = self.executive(message)
            time.sleep(retry)
            if retry >= 100:
                self.message(text=text)

        async def async_except(self, message=None):
            retry, text = self.executive(message)
            await asyncio.sleep(retry)
            if retry >= 100:
                self.message(text=text)
    # ------------------------------------------------------------------------------------------ DEV CHAT END
