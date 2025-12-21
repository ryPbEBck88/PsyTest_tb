from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# from app.data.questions import QUESTIONS

def build_menu_inline() -> InlineKeyboardMarkup:
    """
    Инлайн-меню под сообщениями
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Пройти тест «Твой личный светофор»",
                    callback_data="start_test",
                )
            ],
        ]
    )
