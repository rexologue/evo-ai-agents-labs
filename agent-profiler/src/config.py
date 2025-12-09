import os
import logging
from typing import Optional

from dotenv import load_dotenv, find_dotenv
from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings

# Загрузить .env один раз
load_dotenv(find_dotenv())


# ------------------------------------------------------------------------------
# Логирование
# ------------------------------------------------------------------------------
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("agent-profiler")


# ------------------------------------------------------------------------------
# Продакшн-класс настроек
# ------------------------------------------------------------------------------
class Settings(BaseSettings):

    # ---- LLM ----
    llm_model: str = Field(..., alias="LLM_MODEL")
    llm_api_key: str = Field(..., alias="LLM_API_KEY")
    llm_api_base: str = Field(..., alias="LLM_API_BASE")

    # ---- MCP ----
    db_mcp_url: str = Field(..., alias="DB_MCP_URL")

    # ---- Agent metadata ----
    agent_name: str = Field("CompanyProfiler", alias="AGENT_NAME")
    agent_desc: str = Field(
        "LangChain Agent для формирования профиля компаний",
        alias="AGENT_DESCRIPTION"
    )
    agent_host: str = Field("0.0.0.0", alias="AGENT_HOST")
    agent_port: int = Field(8001, alias="AGENT_PORT")
    agent_url: Optional[str] = Field(None, alias="AGENT_URL")

    agent_version: str = Field("v1.0.0", alias="AGENT_VERSION")

    class Config:
        populate_by_name = True
        extra = "ignore"

    # --------------------------------------------------------------------------
    # Единый post-validator
    # --------------------------------------------------------------------------
    def model_post_init(self, __context):
        """
        ЭТА ФУНКЦИЯ ЗАПУСКАЕТСЯ ОДИН РАЗ ПОСЛЕ ЗАГРУЗКИ ВСЕХ ПОЛЕЙ.
        В продакшене удобно держать всю динамику и derive-логику в одном месте.
        """

        # ----------------------------------------------------------
        # AGENT_URL → вычисляем, если не указан
        # ----------------------------------------------------------
        if not self.agent_url:
            self.agent_url = f"http://{self.agent_host}:{self.agent_port}"
            logger.debug(f"agent_url was empty → set to {self.agent_url}")


# ------------------------------------------------------------------------------
# Фабрика
# ------------------------------------------------------------------------------
_settings_cache: Optional[Settings] = None


def get_settings() -> Settings:
    """Singleton-кеш, чтобы не пересоздавать настройки 100 раз"""
    global _settings_cache
    if _settings_cache is None:
        try:
            _settings_cache = Settings()
        except ValidationError as e:
            logger.error("❌ Invalid configuration:")
            logger.error(e)
            raise
    return _settings_cache
