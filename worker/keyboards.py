import aiogram
import telebot
from typing import Union


class Keys:
    def __init__(self, thread: bool = False):
        self.types = telebot.types if thread else aiogram.types
        self.sb = self.types.KeyboardButton
        self.b = self.types.InlineKeyboardButton

    def keys(self, values=None, inline: bool = True, row_width: int = 2):
        if inline:
            keyboard = self.types.InlineKeyboardMarkup(row_width=row_width)
        else:
            keyboard = self.types.ReplyKeyboardMarkup(row_width=row_width, resize_keyboard=True)
        if values:
            keyboard.add(*values) if type(values) == list else keyboard.add(*[values])
        return keyboard

    def b_cancel(self):
        return self.b('❌ Отмена', callback_data='cancel')

    def picture(self, picture: str = None):
        buttons = [self.b(f"{'Поменять' if picture else 'Прикрепить'} изображение", callback_data='picture')]
        buttons.append(self.b('❌ Удалить изображение', callback_data='picture_remove')) if picture else None
        return buttons

    def post(self, picture: str = None):
        return self.keys([*self.picture(picture), self.b_cancel()])

    def final(self, picture: str = None):
        return self.keys([*self.picture(picture), self.b('Опубликовать', callback_data='publish'), self.b_cancel()])

    def bet(self):
        buttons = []
        for title in ['Live Ставка', 'Ж/Б Ставка', 'Ночная Ставка', 'Бесплатная ставка По линии']:
            buttons.append(self.b(title, callback_data=f'title_{title}'))
        buttons.append(self.b_cancel())
        return self.keys(buttons)
