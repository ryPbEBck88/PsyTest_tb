import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.db import init_db
from app.routers import start, menu, test, admin

logging.basicConfig(level=logging.INFO)


async def main() -> None:
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("Не задан BOT_TOKEN в переменных окружения")

    bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    dp.include_router(start.router)
    dp.include_router(menu.router)
    dp.include_router(test.router)
    dp.include_router(admin.router)

    logging.info("Bot started")
    await dp.start_polling(bot)


if __name__ == "__main__":
    init_db()
    asyncio.run(main())
 