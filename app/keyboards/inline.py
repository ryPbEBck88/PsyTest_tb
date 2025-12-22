import random

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from app.questions import QUESTIONS

LETTERS = ["А", "Б", "В", "Г"]


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