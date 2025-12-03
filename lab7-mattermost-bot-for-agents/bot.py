"""Основной файл бота для Mattermost с интеграцией A2A агента."""
import asyncio
import logging
import signal
import sys
from typing import Optional

from mattermostdriver import Driver

from config import config
from telemetry import setup_telemetry
from a2a_client import A2AClientWrapper
from commands import CommandHandler
from mattermost_handler import MattermostHandler

logger = logging.getLogger(__name__)


class MattermostA2ABot:
    """Основной класс бота."""

    def __init__(self):
        """Инициализация бота."""
        self.driver: Optional[Driver] = None
        self.a2a_client: Optional[A2AClientWrapper] = None
        self.command_handler: Optional[CommandHandler] = None
        self.mattermost_handler: Optional[MattermostHandler] = None
        self._running = False

    async def initialize(self) -> None:
        """Инициализировать все компоненты бота."""
        logger.info("Инициализация бота...")

        # Настройка телеметрии
        setup_telemetry()
        logger.info("Телеметрия настроена")

        # Инициализация A2A клиента
        self.a2a_client = A2AClientWrapper()
        await self.a2a_client.initialize()
        logger.info("A2A клиент инициализирован")

        # Инициализация обработчика команд
        self.command_handler = CommandHandler(self.a2a_client)
        logger.info("Обработчик команд инициализирован")

        # Инициализация Mattermost Driver
        self.driver = Driver(
            {
                "url": config.MATTERMOST_URL,
                "token": config.MATTERMOST_TOKEN,
                "scheme": "https" if config.MATTERMOST_URL.startswith("https") else "http",
                "port": 443 if config.MATTERMOST_URL.startswith("https") else 80,
            }
        )

        # Подключение к Mattermost
        try:
            self.driver.login()
            logger.info("Подключение к Mattermost установлено")
        except Exception as e:
            logger.error(f"Ошибка подключения к Mattermost: {e}")
            raise

        # Инициализация обработчика Mattermost
        self.mattermost_handler = MattermostHandler(
            driver=self.driver,
            a2a_client=self.a2a_client,
            command_handler=self.command_handler,
        )
        await self.mattermost_handler.initialize()
        logger.info("Обработчик Mattermost инициализирован")

        logger.info("Бот успешно инициализирован")

    async def start(self) -> None:
        """Запустить бота."""
        if self._running:
            logger.warning("Бот уже запущен")
            return

        if not self.driver or not self.mattermost_handler:
            raise RuntimeError("Бот не инициализирован. Вызовите initialize() сначала.")

        logger.info("Запуск бота...")
        self._running = True

        # Создаем обработчик событий
        event_handler = self.mattermost_handler.create_event_handler()

        # Инициализируем WebSocket соединение
        try:
            self.driver.init_websocket(event_handler)
            logger.info("WebSocket соединение установлено, бот готов к работе")
        except Exception as e:
            logger.error(f"Ошибка инициализации WebSocket: {e}")
            self._running = False
            raise

        # Ждем пока бот работает
        try:
            while self._running:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Получен сигнал остановки")
            await self.stop()

    async def stop(self) -> None:
        """Остановить бота."""
        if not self._running:
            return

        logger.info("Остановка бота...")
        self._running = False

        # Закрываем A2A клиент
        if self.a2a_client:
            await self.a2a_client.close()

        # Закрываем WebSocket если нужно
        if self.driver:
            try:
                # mattermostdriver может не иметь явного метода закрытия WebSocket
                # но мы можем просто завершить соединение
                pass
            except Exception as e:
                logger.warning(f"Ошибка при закрытии WebSocket: {e}")

        logger.info("Бот остановлен")

    def setup_signal_handlers(self) -> None:
        """Настроить обработчики сигналов для graceful shutdown."""
        def signal_handler(signum, frame):
            logger.info(f"Получен сигнал {signum}, останавливаем бота...")
            asyncio.create_task(self.stop())

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)


async def main():
    """Главная функция."""
    try:
        # Валидация конфигурации
        if not config.validate():
            logger.error("Ошибка валидации конфигурации")
            sys.exit(1)

        # Создание и инициализация бота
        bot = MattermostA2ABot()
        bot.setup_signal_handlers()
        await bot.initialize()

        # Запуск бота
        await bot.start()

    except KeyboardInterrupt:
        logger.info("Прервано пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())


