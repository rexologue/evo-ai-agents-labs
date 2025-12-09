import os
import logging
from pathlib import Path
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

    # ---- System prompt ----
    agent_sys_prompt: Optional[str] = Field(None, alias="AGENT_SYSTEM_PROMPT")

    # Путь до файла, если задан
    agent_sys_prompt_file: Optional[str] = Field(None, alias="AGENT_SYSTEM_PROMPT_FILE")

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
        # 1) AGENT_URL → вычисляем, если не указан
        # ----------------------------------------------------------
        if not self.agent_url:
            self.agent_url = f"http://{self.agent_host}:{self.agent_port}"
            logger.debug(f"agent_url was empty → set to {self.agent_url}")

        # ----------------------------------------------------------
        # 2) System prompt → берём из переменной или файла
        # ----------------------------------------------------------
        # Если PROMPT уже задан в .env → просто чистим кавычки
        if self.agent_sys_prompt:
            cleaned = self.agent_sys_prompt.strip().strip('"').strip("'")
            self.agent_sys_prompt = cleaned
            logger.debug("Using AGENT_SYSTEM_PROMPT directly from env")
            return

        # Если PROMPT в .env не был задан → возможно есть файл
        if self.agent_sys_prompt_file:
            prompt_path = Path(self.agent_sys_prompt_file)

            if not prompt_path.exists():
                logger.warning(
                    f"AGENT_SYSTEM_PROMPT_FILE is set but file does not exist: {prompt_path}"
                )
                self.agent_sys_prompt = self._default_prompt()
                return

            try:
                text = prompt_path.read_text(encoding="utf-8").strip()
                self.agent_sys_prompt = text
                logger.debug(f"Loaded system prompt from file: {prompt_path}")
                return
            
            except Exception as e:
                logger.error(f"Failed to read {prompt_path}: {e}")
                self.agent_sys_prompt = self._default_prompt()
                return

        # Ничего не задано → дефолт
        self.agent_sys_prompt = self._default_prompt()

    # --------------------------------------------------------------------------
    @staticmethod
    def _default_prompt() -> str:
        return (
            "Ты полезный AI-ассистент. Используй доступные инструменты для решения задач "
            "пользователя, запрашивай уточнения, если данных недостаточно."
        )


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
