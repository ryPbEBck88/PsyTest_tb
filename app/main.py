import asyncio
import logging
import os
from dataclasses import dataclass

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    FSInputFile,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from .questions import QUESTIONS, interpret_score, get_result_image_name
from app.db import init_db, save_user
from app.promo import schedule_promo


logging.basicConfig(level=logging.INFO)


@dataclass
class UserSession:
    current_index: int = 0
    score: int = 0


# Простое хранение состояния в памяти
SESSIONS: dict[int, UserSession] = {}

def get_main_keyboard() -> ReplyKeyboardMarkup:
    # Нижняя большая кнопка "Меню"
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Меню")]],
        resize_keyboard=True,
    )


def build_menu_inline() -> InlineKeyboardMarkup:
    # Кнопки под сообщением
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



def build_question_keyboard(q_index: int) -> InlineKeyboardMarkup:
    question = QUESTIONS[q_index]
    letters = ["А", "Б", "В", "Г"]

    rows = [
        [
            InlineKeyboardButton(
                text=letters[i],                   # текст кнопки: А / Б / В / Г
                callback_data=f"answer:{opt.points}"
            )
        ]
        for i, opt in enumerate(question.options)
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)



async def send_question(message: Message, q_index: int) -> None:
    question = QUESTIONS[q_index]
    kb = build_question_keyboard(q_index)
    letters = ["А", "Б", "В", "Г"]

    lines = [
        f"Вопрос {q_index + 1}/{len(QUESTIONS)}",
        "",
        question.text,
        "",
    ]
    for i, opt in enumerate(question.options):
        lines.append(f"{letters[i]}) {opt.text}")

    text = "\n".join(lines)
    await message.answer(text, reply_markup=kb)


async def send_question_cb(callback: CallbackQuery, q_index: int) -> None:
    question = QUESTIONS[q_index]
    kb = build_question_keyboard(q_index)
    letters = ["А", "Б", "В", "Г"]

    lines = [
        f"Вопрос {q_index + 1}/{len(QUESTIONS)}",
        "",
        question.text,
        "",
    ]
    for i, opt in enumerate(question.options):
        lines.append(f"{letters[i]}) {opt.text}")

    text = "\n".join(lines)
    await callback.message.edit_text(text, reply_markup=kb)



async def start_handler(message: Message) -> None:
    user_id = message.from_user.id

    # 1. Сохраняем пользователя
    save_user(message)

    # 2. Запускаем сессию теста
    SESSIONS[user_id] = UserSession(current_index=0, score=0)

    await message.answer(
        "Это тест «Твой личный светофор» — быстрая диагностика внутреннего состояния.\n\n"
        "Отвечай быстро, выбирай то, что чаще всего откликается. "
        "Всего 7 вопросов, 4 варианта ответа.\n\nПоехали!"
    )

    # 3. Запускаем фоновую задачу с отложенной рекламой
    asyncio.create_task(
        schedule_promo(
            bot=message.bot,
            chat_id=message.chat.id,
            telegram_id=message.from_user.id,
        )
    )

    # 4. Первый вопрос
    await send_question(message, 0)



async def menu_handler(message: Message) -> None:
    kb = build_menu_inline()
    await message.answer(
        "Меню:\n\nВыбери действие:",
        reply_markup=kb,
    )


async def start_test_callback(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    SESSIONS[user_id] = UserSession(current_index=0, score=0)

    await callback.message.answer(
        """Этот тест- «твой личный светофор», который показывает твое внутреннее состояние психики.
Пройди короткий тест и узнай, насколько ты нуждаешься в перезагрузке. Это поможет понять, какой поддержки тебе больше всего не хватает.
Отвечайте быстро, первое, что приходит в голову. Выбери тот вариант, который отзывается чаще всего.""",
        reply_markup=get_main_keyboard(),
    )

    await send_question(callback.message, 0)
    await callback.answer()



async def answer_handler(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    session = SESSIONS.get(user_id)

    if session is None:
        SESSIONS[user_id] = UserSession()
        session = SESSIONS[user_id]

    data = callback.data or ""
    try:
        _, points_str = data.split(":")
        points = int(points_str)
    except Exception:
        await callback.answer("Ошибка данных ответа. Попробуй ещё раз.", show_alert=True)
        return

    # добавляем баллы и двигаемся к следующему вопросу
    session.score += points
    session.current_index += 1

    # === ФИНАЛ ТЕСТА ===
    if session.current_index >= len(QUESTIONS):
        score = session.score
        result_text = interpret_score(score)  # весь длинный текст остаётся

        # короткий уровень для подписи к фото
        if score <= 17:
            level = "ЗЕЛЕНЫЙ УРОВЕНЬ"
        elif score <= 34:
            level = "ЖЕЛТЫЙ УРОВЕНЬ"
        elif score <= 52:
            level = "КРАСНЫЙ УРОВЕНЬ"
        else:
            level = "МИГАЮЩИЙ КРАСНЫЙ"

        # очищаем сессию
        if user_id in SESSIONS:
            del SESSIONS[user_id]

        # путь к картинке
        image_name = get_result_image_name(score)
        base_dir = os.path.dirname(__file__)
        image_path = os.path.join(base_dir, "images", image_name)

        await callback.message.edit_text("Тест завершён. Считаем результат…")

        photo = FSInputFile(image_path)
        caption = f"{level}\nТвои баллы: {score}"

        # 1) отправляем фото с КОРОТКОЙ подписью
        await callback.message.answer_photo(photo=photo, caption=caption)
        # 2) отдельным сообщением — полный текст интерпретации
        await callback.message.answer(result_text)

        await callback.answer()
        return

    # === СЛЕДУЮЩИЙ ВОПРОС ===
    await send_question_cb(callback, session.current_index)
    await callback.answer()




def setup_routes(dp: Dispatcher) -> None:
    dp.message.register(start_handler, CommandStart())
    dp.message.register(menu_handler, F.text == "Меню")
    dp.callback_query.register(start_test_callback, F.data == "start_test")
    dp.callback_query.register(answer_handler, F.data.startswith("answer:"))



async def main() -> None:
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("Не задан BOT_TOKEN в переменных окружения")

    bot = Bot(
        token=token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    setup_routes(dp)

    logging.info("Bot started")
    await dp.start_polling(bot)



if __name__ == "__main__":
    init_db()
    asyncio.run(main())
    