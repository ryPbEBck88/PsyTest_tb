import asyncio
import html
import logging
from typing import Optional

from aiogram import Bot


class TelegramLogHandler(logging.Handler):
    """Handler для отправки ошибок и критических сообщений в Telegram"""
    
    def __init__(self, bot: Bot, chat_id: int, level=logging.ERROR):
        super().__init__(level)
        self.bot = bot
        self.chat_id = chat_id
        self._queue: Optional[asyncio.Queue] = None
        self._task: Optional[asyncio.Task] = None
    
    def set_queue(self, queue: asyncio.Queue):
        """Устанавливает очередь для отправки сообщений"""
        self._queue = queue
    
    def emit(self, record: logging.LogRecord) -> None:
        """Отправляет сообщение об ошибке в Telegram через очередь"""
        try:
            message = self.format(record)
            
            # Ограничиваем длину сообщения (максимум 4096 символов для Telegram)
            if len(message) > 4000:
                message = message[:4000] + "\n... (сообщение обрезано)"
            
            # Добавляем сообщение в очередь для асинхронной отправки
            if self._queue:
                try:
                    self._queue.put_nowait(message)
                except asyncio.QueueFull:
                    # Если очередь переполнена, просто игнорируем
                    pass
        except Exception:
            # Игнорируем ошибки в самом handler, чтобы не попасть в бесконечный цикл
            self.handleError(record)
    
    async def _send_message(self, text: str) -> None:
        """Асинхронная отправка сообщения"""
        try:
            # Экранируем HTML символы для безопасности
            escaped_text = html.escape(text)
            
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=f"<b>Ошибка в боте:</b>\n\n<code>{escaped_text}</code>",
                parse_mode="HTML"
            )
        except Exception:
            # Игнорируем ошибки отправки, чтобы не блокировать логирование
            pass
    
    async def _message_sender(self) -> None:
        """Фоновая задача для отправки сообщений из очереди"""
        while True:
            try:
                message = await self._queue.get()
                await self._send_message(message)
                self._queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception:
                # Игнорируем ошибки, продолжаем работу
                pass
    
    def start_sender(self) -> None:
        """Запускает фоновую задачу для отправки сообщений"""
        if self._queue and not self._task:
            self._task = asyncio.create_task(self._message_sender())
    
    def stop_sender(self) -> None:
        """Останавливает фоновую задачу"""
        if self._task:
            self._task.cancel()
            self._task = None


def setup_telegram_logging(bot: Bot, chat_id: int, level=logging.ERROR) -> TelegramLogHandler:
    """Настраивает отправку ошибок в Telegram"""
    handler = TelegramLogHandler(bot, chat_id, level)
    handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s\n'
        'File: %(pathname)s:%(lineno)d\n'
        'Function: %(funcName)s'
    ))
    
    # Добавляем handler к корневому logger
    logger = logging.getLogger()
    logger.addHandler(handler)
    
    return handler


async def start_telegram_logging_handler(handler: TelegramLogHandler) -> None:
    """Запускает обработчик логов (должен вызываться из async функции)"""
    queue = asyncio.Queue(maxsize=100)  # Максимум 100 сообщений в очереди
    handler.set_queue(queue)
    handler.start_sender()

