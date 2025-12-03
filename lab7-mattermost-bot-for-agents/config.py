"""Конфигурация бота из переменных окружения."""
import os
import logging
from typing import Optional
from dotenv import load_dotenv

# Загружаем .env файл если он существует (для разработки)
load_dotenv()

logger = logging.getLogger(__name__)


class Config:
    """Класс для хранения конфигурации бота."""

    # Mattermost настройки
    MATTERMOST_URL: str
    MATTERMOST_TOKEN: str
    MATTERMOST_BOT_USERNAME: Optional[str] = None

    # A2A настройки
    A2A_BASE_URL: str
    A2A_TOKEN: str

    # OpenTelemetry настройки
    OTEL_EXPORTER_OTLP_ENDPOINT: str
    OTEL_SERVICE_NAME: str = "mattermost-a2a-bot"

    # Логирование
    LOG_LEVEL: str = "INFO"

    def __init__(self):
        """Инициализация конфигурации из переменных окружения."""
        # Mattermost
        self.MATTERMOST_URL = self._get_required_env("MATTERMOST_URL")
        self.MATTERMOST_TOKEN = self._get_required_env("MATTERMOST_TOKEN")
        self.MATTERMOST_BOT_USERNAME = os.getenv("MATTERMOST_BOT_USERNAME")

        # A2A
        self.A2A_BASE_URL = self._get_required_env("A2A_BASE_URL")
        self.A2A_TOKEN = self._get_required_env("A2A_TOKEN")

        # OpenTelemetry
        self.OTEL_EXPORTER_OTLP_ENDPOINT = self._get_required_env(
            "OTEL_EXPORTER_OTLP_ENDPOINT"
        )
        self.OTEL_SERVICE_NAME = os.getenv(
            "OTEL_SERVICE_NAME", "mattermost-a2a-bot"
        )

        # Логирование
        log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        self.LOG_LEVEL = log_level

        # Настройка логирования
        logging.basicConfig(
            level=getattr(logging, log_level, logging.INFO),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )

    def _get_required_env(self, key: str) -> str:
        """Получить обязательную переменную окружения."""
        value = os.getenv(key)
        if not value:
            raise ValueError(f"Обязательная переменная окружения {key} не установлена")
        return value

    def validate(self) -> bool:
        """Проверить корректность конфигурации."""
        try:
            # Проверяем, что все обязательные поля установлены
            assert self.MATTERMOST_URL, "MATTERMOST_URL не установлен"
            assert self.MATTERMOST_TOKEN, "MATTERMOST_TOKEN не установлен"
            assert self.A2A_BASE_URL, "A2A_BASE_URL не установлен"
            assert self.A2A_TOKEN, "A2A_TOKEN не установлен"
            assert self.OTEL_EXPORTER_OTLP_ENDPOINT, "OTEL_EXPORTER_OTLP_ENDPOINT не установлен"
            return True
        except AssertionError as e:
            logger.error(f"Ошибка валидации конфигурации: {e}")
            return False


# Глобальный экземпляр конфигурации
config = Config()


