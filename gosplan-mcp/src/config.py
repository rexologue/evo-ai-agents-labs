"""Загрузка настроек окружения для gosplan-mcp."""

from __future__ import annotations

import logging
import os
from typing import Optional

from dotenv import find_dotenv, load_dotenv
from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings

load_dotenv(find_dotenv())

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("gosplan-mcp")


class Settings(BaseSettings):
    """Настройки MCP транспорта."""

    server_port: int = Field(..., alias="MCP_PORT")
    server_host: str = Field(..., alias="MCP_HOST")


_settings_cache: Optional[Settings] = None


def get_settings() -> Settings:
    """Возвращает кэшированный экземпляр настроек."""

    global _settings_cache

    if _settings_cache is None:
        try:
            _settings_cache = Settings()
        except ValidationError as exc:
            logger.error("❌ Invalid configuration:")
            logger.error(exc)
            raise

    return _settings_cache
