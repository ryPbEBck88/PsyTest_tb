import asyncio
import os

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove

from app.keyboards.inline import build_menu_inline
from app.promo import schedule_promo
from app.db import user_exists

# сессия и отправка первого вопроса живут в test.py
from app.routers.test import SESSIONS, UserSession, send_question

router = Router()


@router.message(F.text == "Меню")
async def menu_handler(message: Message) -> None:
    kb = build_menu_inline()
    await message.answer(
        "Меню:\n\nВыбери действие:",
        reply_markup=kb,
    )


@router.callback_query(F.data == "start_test")
async def start_test_callback(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    bot = callback.message.bot

    # Стартуем сессию теста
    SESSIONS[user_id] = UserSession(current_index=0, score=0)

    # Уведомляем хозяйку бота (ADMIN_ID должен быть в .env)
    admin_id = int(os.getenv("ADMIN_ID"))

    username = callback.from_user.username
    full_name = callback.from_user.full_name or ""

    if username:
        user_label = f"@{username}"
    elif full_name:
        user_label = full_name
    else:
        user_label = f"ID: {user_id}"

    if not user_exists(user_id):
        await bot.send_message(
            admin_id,
            f"Новый пользователь начал проходить тест: {user_label}",
        )

    # Фоновая задача с отложенной рекламой
    asyncio.create_task(
        schedule_promo(
            bot=bot,
            chat_id=callback.message.chat.id,
            telegram_id=user_id,
        )
    )

    # Приветствие теста
    await callback.message.answer(
        "Этот тест — «Твой личный светофор», который показывает твое внутреннее состояние психики.\n\n"
        "Пройди короткий тест и узнай, насколько ты нуждаешься в перезагрузке. "
        "Это поможет понять, какой поддержки тебе больше всего не хватает.\n\n"
        "Отвечай быстро, первое, что приходит в голову. "
        "Выбери тот вариант, который отзывается чаще всего.",
        reply_markup=ReplyKeyboardRemove(),  # убираем нижнюю кнопку "Меню" на время теста
    )

    # Первый вопрос
    await send_question(callback.message, 0)
    await callback.answer()
