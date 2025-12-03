from pydantic_settings import BaseSettings
from dotenv import find_dotenv
from functools import lru_cache
from typing import Optional

class _Settings(BaseSettings):
    class Config:
        env_file_encoding = "utf-8"
        extra = "allow"

class Config(_Settings):
    TELEGRAM_BOT_TOKEN: str
    TELEGRAM_BOT_USERNAME: str
    PUBLIC_URL: str
    HANDLE_MESSAGE_EDITS: bool = True  # Обрабатывать измененные сообщения
    HANDLE_MESSAGE_DELETES: bool = False  # Игнорировать удаленные сообщения
    EDIT_RESPONSE_TIMEOUT: int = 30  # Таймаут для отмены старого запроса (секунды)

@lru_cache()
def get_config(env_file: str = ".env") -> Config:
    return Config(_env_file=find_dotenv(env_file)) # type: ignore

# Create a typed instance
config: Config = get_config()