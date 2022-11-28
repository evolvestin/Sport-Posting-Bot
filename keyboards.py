import aiogram
import telebot
sport = {'Хоккей': '🏒', 'Футбол': '⚽', 'Теннис': '🎾', 'Волейбол': '🏐',
         'Баскетбол': '🏀', 'Киберспорт': '🕹', 'Настольный теннис': '🏓'}


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

    def b_back(self):
        return self.b('⬅ Назад', callback_data='back')

    def b_cancel(self):
        return self.b('❌ Отмена', callback_data='cancel')

    def picture(self, picture: str = None):
        key = 'Поменять' if picture and picture != 'removed' else 'Прикрепить'
        buttons = [self.b(f"{key} изображение", callback_data='picture')]
        if picture and picture != 'removed':
            buttons.append(self.b('❌ Удалить изображение', callback_data='picture_remove'))
        return buttons

    def post(self, picture: str = None):
        return self.keys([*self.picture(picture), self.b_back(), self.b_cancel()])

    def final(self, picture: str = None):
        return self.keys([*self.picture(picture), self.b_back(),
                          self.b('Опубликовать', callback_data='publish'), self.b_cancel()])

    def bet(self):
        buttons = []
        for title in ['Live Ставка', 'Ж/Б Ставка', 'Ночная Ставка', 'Бесплатная ставка По линии']:
            buttons.append(self.b(title, callback_data=f'title_{title}'))
        buttons.append(self.b_cancel())
        return self.keys(buttons)

    def sport(self):
        buttons = []
        for sport_type, sport_emoji in sport.items():
            button_text = f'{sport_emoji} {sport_type} {sport_emoji}'
            buttons.append(self.b(button_text, callback_data=f'sport_{sport_type}'))
        buttons.append(self.b_cancel())
        return self.keys(buttons)
