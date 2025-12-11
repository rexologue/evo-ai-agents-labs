"""Настройки агента подбора закупок."""
import os
import logging
from typing import Optional

from dotenv import load_dotenv, find_dotenv
from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings

# Загружаем .env
load_dotenv(find_dotenv())

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("purchase_matcher")


class Settings(BaseSettings):
    """Параметры окружения для агента подбора закупок."""

    # ---- LLM ----
    llm_model: str = Field(..., alias="LLM_MODEL")
    llm_api_key: str = Field(..., alias="LLM_API_KEY")
    llm_api_base: str = Field(..., alias="LLM_API_BASE")

    # ---- MCP ----
    db_mcp_url: str = Field(..., alias="DB_MCP_URL")
    gosplan_mcp_url: str = Field(..., alias="GOSPLAN_MCP_URL")

    # ---- Agent metadata ----
    agent_name: str = Field("PurchaseMatcher", alias="AGENT_NAME")
    agent_desc: str = Field(
        "Агент подбирает закупки ЕИС для заданной компании по профилю и запросу",
        alias="AGENT_DESCRIPTION",
    )
    agent_host: str = Field("0.0.0.0", alias="AGENT_HOST")
    agent_port: int = Field(8002, alias="AGENT_PORT")
    agent_url: Optional[str] = Field(None, alias="AGENT_URL")
    agent_version: str = Field("v1.0.0", alias="AGENT_VERSION")

    class Config:
        populate_by_name = True
        extra = "ignore"

    def model_post_init(self, __context):
        if not self.agent_url:
            self.agent_url = f"http://{self.agent_host}:{self.agent_port}"


_settings_cache: Optional[Settings] = None


def get_settings() -> Settings:
    """Возвращает singleton настроек."""
    global _settings_cache
    if _settings_cache is None:
        try:
            _settings_cache = Settings()
        except ValidationError as exc:
            logger.error("❌ Invalid configuration:")
            logger.error(exc)
            raise
    return _settings_cache
