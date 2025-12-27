import os
from aiogram import F, Router
from aiogram.types import CallbackQuery

from app.db import get_recent_users

router = Router(name=__name__)
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))


def format_user_label(telegram_id: int, username: str | None, first_name: str | None, last_name: str | None) -> str:
    """Форматирует метку пользователя для отображения"""
    full_name = None
    if first_name or last_name:
        full_name = " ".join(filter(None, [first_name, last_name]))
    
    if username:
        return f"@{username}"
    elif full_name:
        return f'<a href="tg://user?id={telegram_id}">{full_name}</a>'
    else:
        return f"ID: {telegram_id}"


@router.callback_query(F.data == "admin_recent_users")
async def recent_users_handler(callback: CallbackQuery) -> None:
    """Обработчик кнопки для администратора: показывает последних 10 пользователей"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Доступ запрещен", show_alert=True)
        return
    
    users = get_recent_users(10)
    
    if not users:
        await callback.message.answer("Пользователей пока нет.")
        await callback.answer()
        return
    
    lines = ["<b>Последние пользователи:</b>\n"]
    
    for i, (telegram_id, username, first_name, last_name, created_at, score) in enumerate(users, 1):
        user_label = format_user_label(telegram_id, username, first_name, last_name)
        score_text = f", результат: {score}" if score else ""
        lines.append(f"{i}. {user_label}{score_text}")
    
    text = "\n".join(lines)
    await callback.message.answer(text)
    await callback.answer()

