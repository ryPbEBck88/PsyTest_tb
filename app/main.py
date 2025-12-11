import asyncio
import logging
import os
from dataclasses import dataclass

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    FSInputFile,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

from app.db import init_db, save_user, get_user_first_name
from app.promo import schedule_promo
from .questions import QUESTIONS, interpret_score, get_result_image_name


logging.basicConfig(level=logging.INFO)
admin_id = int(os.getenv("ADMIN_ID"))


@dataclass
class UserSession:
    current_index: int = 0
    score: int = 0


# Простое хранение состояния в памяти
SESSIONS: dict[int, UserSession] = {}


def get_main_keyboard() -> ReplyKeyboardMarkup:
    """
    Нижняя большая кнопка "Меню"
    """
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Меню")]],
        resize_keyboard=True,
    )


def build_menu_inline() -> InlineKeyboardMarkup:
    """
    Инлайн-меню под сообщением
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


def build_question_keyboard(q_index: int) -> InlineKeyboardMarkup:
    """
    Клавиатура с вариантами ответов А/Б/В/Г
    """
    question = QUESTIONS[q_index]
    letters = ["А", "Б", "В", "Г"]

    rows = [
        [
            InlineKeyboardButton(
                text=letters[i],
                callback_data=f"answer:{opt.points}",
            )
        ]
        for i, opt in enumerate(question.options)
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def send_question(message: Message, q_index: int) -> None:
    """
    Отправка вопроса (новым сообщением)
    """
    question = QUESTIONS[q_index]
    kb = build_question_keyboard(q_index)
    letters = ["А", "Б", "В", "Г"]

    lines: list[str] = [
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
    """
    Обновление уже существующего сообщения с вопросом
    """
    question = QUESTIONS[q_index]
    kb = build_question_keyboard(q_index)
    letters = ["А", "Б", "В", "Г"]

    lines: list[str] = [
        f"Вопрос {q_index + 1}/{len(QUESTIONS)}",
        "",
        question.text,
        "",
    ]

    for i, opt in enumerate(question.options):
        lines.append(f"{letters[i]}) {opt.text}")

    text = "\n".join(lines)
    await callback.message.edit_text(text, reply_markup=kb)


# -------------------- HANDLERS --------------------


async def start_handler(message: Message) -> None:
    """
    /start: приветствие + нижняя кнопка "Меню".
    Тест сразу не начинаем.
    """
    # Сохраняем пользователя в БД
    save_user(message)

    await message.answer(
        "Привет! Это бот с тестом «Твой личный светофор».\n\n"
        "Нажми кнопку «Меню» внизу, чтобы выбрать действие.",
        reply_markup=get_main_keyboard(),
    )


async def menu_handler(message: Message) -> None:
    """
    Нажатие кнопки "Меню" (reply-клавиатура).
    Показываем инлайн-меню с кнопкой запуска теста.
    """
    kb = build_menu_inline()
    await message.answer(
        "Меню:\n\nВыбери действие:",
        reply_markup=kb,
    )


async def start_test_callback(callback: CallbackQuery) -> None:
    """
    Нажатие инлайн-кнопки "Пройти тест…".
    Здесь запускаем сессию теста, рекламу и задаём первый вопрос.
    """
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

    await bot.send_message(
        admin_id,
        f"Новый пользователь начал проходить тест: {user_label}"
    )


    # Фоновая задача с отложенной рекламой
    asyncio.create_task(
        schedule_promo(
            bot=callback.message.bot,
            chat_id=callback.message.chat.id,
            telegram_id=user_id,
        )
    )

    # Приветствие теста
    await callback.message.answer(
        (
            "Этот тест — «Твой личный светофор», который показывает твое внутреннее состояние психики.\n\n"
            "Пройди короткий тест и узнай, насколько ты нуждаешься в перезагрузке. "
            "Это поможет понять, какой поддержки тебе больше всего не хватает.\n\n"
            "Отвечай быстро, первое, что приходит в голову. "
            "Выбери тот вариант, который отзывается чаще всего."
        ),
        reply_markup=ReplyKeyboardRemove(),  # убираем нижнюю кнопку "Меню" на время теста
    )

    # Первый вопрос
    await send_question(callback.message, 0)
    await callback.answer()


async def answer_handler(callback: CallbackQuery) -> None:
    """
    Обработка ответов на вопросы: callback_data='answer:<points>'
    """
    user_id = callback.from_user.id
    session = SESSIONS.get(user_id)

    if session is None:
        # Если по какой-то причине сессии нет — создаём новую
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

        # Путь к картинке
        image_name = get_result_image_name(score)
        base_dir = os.path.dirname(__file__)
        image_path = os.path.join(base_dir, "images", image_name)

        await callback.message.edit_text("Тест завершён. Считаем результат…")

        photo = FSInputFile(image_path)
        caption = f"{level}\nТвои баллы: {score}"

        # 1) Фото с короткой подписью
        await callback.message.answer_photo(photo=photo, caption=caption)
        # 2) Полный текст интерпретации
        await callback.message.answer(result_text)
        # 3) Возвращаем нижнюю кнопку "Меню"
        await callback.message.answer(
            "Если хочешь, можешь вернуться в меню и пройти тест ещё раз или поделиться им.",
            reply_markup=get_main_keyboard(),
        )

        await callback.answer()
        return

    # --- СЛЕДУЮЩИЙ ВОПРОС ---
    await send_question_cb(callback, session.current_index)
    await callback.answer()


# -------------------- ROUTES / MAIN --------------------


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
