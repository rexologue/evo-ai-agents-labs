"""Загрузка настроек окружения для gosplan-mcp."""

from __future__ import annotations

import logging
import os
from functools import lru_cache

from dotenv import find_dotenv, load_dotenv
from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv(find_dotenv())

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("gosplan-mcp")


class Settings(BaseSettings):
    """Настройки MCP сервера и обращений к ГосПлан API."""

    model_config = SettingsConfigDict(extra="ignore", env_prefix="", env_file=".env")

    server_port: int = Field(..., alias="MCP_PORT", ge=1, le=65535)
    server_host: str = Field(..., alias="MCP_HOST")

    gosplan_base_url: AnyHttpUrl = Field(
        "https://v2test.gosplan.info",
        alias="GOSPLAN_BASE_URL",
        description="Базовый URL API ГосПлан",
    )
    gosplan_timeout_seconds: float = Field(
        20.0,
        alias="GOSPLAN_TIMEOUT",
        description="Таймаут HTTP-запросов к ГосПлан, сек.",
        ge=1,
        le=120,
    )
    purchases_limit: int = Field(
        9,
        alias="GOSPLAN_PURCHASES_LIMIT",
        description="Ограничение на количество закупок за один вызов",
        ge=1,
        le=50,
    )


@lru_cache
def get_settings() -> Settings:
    """Возвращает кэшированный экземпляр настроек."""

    return Settings()
