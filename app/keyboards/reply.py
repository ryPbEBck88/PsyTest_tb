from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_main_keyboard() -> ReplyKeyboardMarkup:
    """
    Нижняя большая кнопка "Меню"
    """
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Меню")]],
        resize_keyboard=True,
    )
