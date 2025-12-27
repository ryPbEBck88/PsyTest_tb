import asyncio
import os
from dataclasses import dataclass

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message, FSInputFile

from app.db import update_score
from app.keyboards.inline import (
    build_question_text_and_kb,
    build_result_kb_for_page,
    RESULT_PAGE_CB_PREFIX
)
from app.keyboards.reply import get_main_keyboard
from app.questions import QUESTIONS, interpret_score, get_result_image_name

router = Router()
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))


@dataclass
class UserSession:
    current_index: int = 0
    score: int = 0


# Простое хранение состояния в памяти
SESSIONS: dict[int, UserSession] = {}
PAGE_SIZE = 700
RESULT_PAGES: dict[int, list[str]] = {}

def split_text(text: str, size: int = PAGE_SIZE) -> list[str]:
    """
    Разбивает текст на накопительные страницы:
    - страница 0: первые size символов
    - страница 1: первые 2*size символов
    - страница 2: первые 3*size символов
    и т.д.
    """
    pages = []
    current_length = size
    text_length = len(text)
    
    while current_length < text_length:
        pages.append(text[:current_length])
        current_length += size
    
    # Добавляем последнюю страницу со всем оставшимся текстом
    # Проверяем, что последняя страница отличается от предыдущей
    if text_length > 0 and (len(pages) == 0 or len(text) > len(pages[-1])):
        pages.append(text)
    
    return pages


async def send_question(message: Message, q_index: int) -> None:
    """
    Отправка вопроса (новым сообщением)
    """
    text, kb = build_question_text_and_kb(q_index)
    await message.answer(text, reply_markup=kb)


async def send_question_cb(callback: CallbackQuery, q_index: int) -> None:
    """
    Обновление уже существующего сообщения с вопросом
    """
    text, kb = build_question_text_and_kb(q_index)
    await callback.message.edit_text(text, reply_markup=kb)


@router.callback_query(F.data.startswith("answer:"))
async def answer_handler(callback: CallbackQuery) -> None:
    """
    Обработка ответов на вопросы: callback_data='answer:<points>'
    """
    user_id = callback.from_user.id
    bot = callback.message.bot

    session = SESSIONS.get(user_id)
    if session is None:
        session = UserSession()
        SESSIONS[user_id] = session

    data = callback.data or ""
    try:
        _, points_str = data.split(":")
        points = int(points_str)
    except Exception:
        await callback.answer("Ошибка данных ответа. Попробуй ещё раз.", show_alert=True)
        return

    # Добавляем баллы и двигаемся к следующему вопросу
    session.score += points
    session.current_index += 1

    # --- ФИНАЛ ТЕСТА ---
    if session.current_index >= len(QUESTIONS):
        score = session.score
        result_text = interpret_score(score)

        # Краткий уровень для подписи к фото
        if score <= 17:
            level = "ЗЕЛЕНЫЙ УРОВЕНЬ"
        elif score <= 34:
            level = "ЖЕЛТЫЙ УРОВЕНЬ"
        elif score <= 52:
            level = "КРАСНЫЙ УРОВЕНЬ"
        else:
            level = "МИГАЮЩИЙ КРАСНЫЙ"

        # Очищаем сессию
        if user_id in SESSIONS:
            del SESSIONS[user_id]

        # Путь к картинке (как в твоём main.py: рядом с этим файлом папка images)
        image_name = get_result_image_name(score)
        base_dir = os.path.dirname(__file__)
        image_path = os.path.join(base_dir, "images", image_name)

        await callback.message.edit_text("Тест завершён. Считаем результат…")

        await asyncio.sleep(2)

        photo = FSInputFile(image_path)
        caption = f"{level}\nТвои баллы: {score}"

        # 1) Фото с короткой подписью
        await callback.message.answer_photo(photo=photo, caption=caption)

        await asyncio.sleep(2)

        # 2) Текст интерпретации частями + кнопка "Подробнее"
        pages = split_text(result_text)
        RESULT_PAGES[user_id] = pages

        kb = build_result_kb_for_page(0, len(pages))
        await callback.message.answer(pages[0], reply_markup=kb)


        # 3) Возвращаем нижнюю кнопку "Меню"
        await callback.message.answer(
            "Если хочешь, можешь вернуться в меню и пройти тест ещё раз или поделиться им.",
            reply_markup=get_main_keyboard(),
        )
        username = callback.from_user.username
        full_name = callback.from_user.full_name or ""

        if username:
            user_label = f"@{username}"
        elif full_name:
            user_label = f'<a href="tg://user?id={user_id}">@{full_name}</a>'
        else:
            user_label = f"ID: {user_id}"

        await bot.send_message(
            ADMIN_ID,
            f"Пользователь {user_label}, результат - {score}"
        )
        update_score(user_id, score)

        await callback.answer()
        return

    # --- СЛЕДУЮЩИЙ ВОПРОС ---
    await send_question_cb(callback, session.current_index)
    await callback.answer()


@router.callback_query(F.data.startswith(RESULT_PAGE_CB_PREFIX))
async def result_more_handler(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    data = callback.data or ""

    try:
        page = int(data.replace(RESULT_PAGE_CB_PREFIX, ""))
    except Exception:
        await callback.answer("Ошибка кнопки.", show_alert=True)
        return

    pages = RESULT_PAGES.get(user_id)
    if not pages:
        await callback.answer("Текст результата уже недоступен. Пройди тест заново.", show_alert=True)
        return

    if page < 0 or page >= len(pages):
        await callback.answer()
        return

    kb = build_result_kb_for_page(page, len(pages))
    await callback.message.edit_text(pages[page], reply_markup=kb)

    # УДАЛЕНИЕ: если показали последнюю страницу — чистим
    if page == len(pages) - 1:
        RESULT_PAGES.pop(user_id, None)

    await callback.answer()
