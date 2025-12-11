# promo.py
import asyncio
from aiogram import Bot
from app.db import is_promo_sent, mark_promo_sent, get_user_first_name

PROMO_DELAY_SECONDS = 24 * 60 * 60  # 24 часа


async def schedule_promo(bot: Bot, chat_id: int, telegram_id: int):
    # Ждём 24 часа
    await asyncio.sleep(PROMO_DELAY_SECONDS)

    # Перед отправкой ещё раз проверяем, не отправляли ли рекламу
    if is_promo_sent(telegram_id):
        return

    first_name = get_user_first_name(telegram_id)

    text = (
        f"{first_name}, привет! "
        "Спасибо, что прошёл(а) тест вчера.\n\n"
        "Если хочешь пойти дальше — у меня есть ещё один инструмент, "
        "который поможет лучше разобраться в себе. Напиши /more."
    )

    try:
        await bot.send_message(chat_id, text)
        mark_promo_sent(telegram_id)
    except Exception:
        # тут можно залогировать ошибку, если хочешь
        pass
