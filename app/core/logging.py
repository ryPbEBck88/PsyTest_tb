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
    
    def _is_critical_error(self, record: logging.LogRecord) -> bool:
        """Проверяет, является ли ошибка критичной"""
        # CRITICAL уровень - всегда критичный
        if record.levelno >= logging.CRITICAL:
            return True
        
        # ERROR уровень - проверяем по типу ошибки
        if record.levelno >= logging.ERROR:
            # Игнорируем некритичные сетевые ошибки
            message = record.getMessage().lower()
            exc_info = record.exc_info
            
            # Список некритичных ошибок, которые можно игнорировать
            non_critical_patterns = [
                'timeout',
                'request timeout',
                'connection timeout',
                'network',
                'telegram network error',
                'telegram server error',
                'http client says',
                'telegram server says',
                'bad gateway',
                'failed to fetch updates',
                'sleep for',
                'try again',
            ]
            
            # Проверяем сообщение
            for pattern in non_critical_patterns:
                if pattern in message:
                    return False
            
            # Проверяем тип исключения
            if exc_info and exc_info[0]:
                exc_type_name = exc_info[0].__name__.lower()
                # Игнорируем сетевые ошибки Telegram API
                non_critical_exceptions = [
                    'telegramnetworkerror',
                    'telegramservererror',
                    'timeouterror',
                    'connectionerror',
                ]
                if any(exc in exc_type_name for exc in non_critical_exceptions):
                    return False
        
        return True
    
    def emit(self, record: logging.LogRecord) -> None:
        """Отправляет сообщение об ошибке в Telegram через очередь"""
        try:
            # Проверяем, критична ли ошибка
            if not self._is_critical_error(record):
                return
            
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
            
            # Определяем заголовок по уровню ошибки из текста
            if "CRITICAL" in text.upper():
                level_name = "🔴 Критическая ошибка"
            else:
                level_name = "⚠️ Ошибка"
            
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=f"<b>{level_name} в боте:</b>\n\n<code>{escaped_text}</code>",
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

