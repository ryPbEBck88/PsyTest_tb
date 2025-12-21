from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from app.db import save_user
from app.keyboards.reply import get_main_keyboard

router = Router(name=__name__)

@router.message(CommandStart())
async def start_handler(message: Message) -> None:
    """
    /start: приветствие + нижняя кнопка "Меню".
    Тест сразу не начинаем.
    """
    save_user(message)

    await message.answer(
        "Привет! Это бот с тестом «Твой личный светофор».\n\n"
        "Нажми кнопку «Меню» внизу, чтобы выбрать действие.",
        reply_markup=get_main_keyboard(),
    )