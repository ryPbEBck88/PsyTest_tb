import asyncio
import logging
import os
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.db import init_db
from app.routers import start, menu, test, admin
from app.core.logging import setup_telegram_logging, start_telegram_logging_handler

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# ID для отправки ошибок (можно вынести в переменную окружения)
ERROR_CHAT_ID = 905551789


async def main() -> None:
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("Не задан BOT_TOKEN в переменных окружения")

    bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    # Настраиваем отправку ошибок в Telegram
    telegram_handler = setup_telegram_logging(bot, ERROR_CHAT_ID, level=logging.ERROR)
    await start_telegram_logging_handler(telegram_handler)

    # Обработчик необработанных исключений
    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        logger = logging.getLogger()
        logger.error(
            "Uncaught exception",
            exc_info=(exc_type, exc_value, exc_traceback)
        )
    
    sys.excepthook = handle_exception

    dp.include_router(start.router)
    dp.include_router(menu.router)
    dp.include_router(test.router)
    dp.include_router(admin.router)

    logging.info("Bot started")
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logging.critical(f"Critical error in bot: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    init_db()
    asyncio.run(main())
 