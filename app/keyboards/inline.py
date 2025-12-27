import random

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from app.questions import QUESTIONS

LETTERS = ["А", "Б", "В", "Г"]
RESULT_PAGE_CB_PREFIX = "result_more:"


def build_menu_inline(is_admin: bool = False) -> InlineKeyboardMarkup:
    """
    Инлайн-меню под сообщением
    """
    keyboard = [
        [
            InlineKeyboardButton(
                text="Пройти тест «Твой личный светофор»",
                callback_data="start_test",
            )
        ],
    ]
    
    if is_admin:
        keyboard.append([
            InlineKeyboardButton(
                text="📊 Последние пользователи",
                callback_data="admin_recent_users",
            )
        ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def build_question_text_and_kb(q_index: int) -> tuple[str, InlineKeyboardMarkup]:
    """
    Строит текст вопроса и инлайн-клавиатуру из одного перемешанного порядка вариантов.
    Очки привязаны к callback_data кнопки, а не к позиции. [web:57]
    """
    question = QUESTIONS[q_index]

    options = list(question.options)
    random.shuffle(options)  # shuffle in-place, поэтому работаем с копией [web:28]

    lines: list[str] = [
        f"Вопрос {q_index + 1}/{len(QUESTIONS)}",
        "",
        question.text,
        "",
    ]

    for i, opt in enumerate(options):
        lines.append(f"{LETTERS[i]}) {opt.text}")

    text = "\n".join(lines)

    rows = [
        [
            InlineKeyboardButton(
                text=LETTERS[i],
                callback_data=f"answer:{opt.points}",
            )
        ]
        for i, opt in enumerate(options)
    ]
    kb = InlineKeyboardMarkup(inline_keyboard=rows)

    return text, kb


def build_result_more_kb(next_page: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Подробнее ▶", callback_data=f"{RESULT_PAGE_CB_PREFIX}{next_page}")]
        ]
    )

def build_result_kb_for_page(page: int, total_pages: int) -> InlineKeyboardMarkup | None:
    # если дальше страниц нет — клавиатуру не показываем
    if page >= total_pages - 1:
        return None
    return build_result_more_kb(page + 1)
