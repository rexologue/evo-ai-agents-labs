from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    db_host: str = Field(..., alias="DB_HOST")
    db_port: int = Field(..., alias="DB_PORT")
    db_name: str = Field(..., alias="DB_NAME")
    db_user: str = Field(..., alias="DB_USER")
    db_password: str = Field(..., alias="DB_PASSWORD")
    server_port: int = Field(..., alias="DB_MCP_PORT")
    server_host: str = Field(..., alias="DB_MCP_HOST")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


def get_settings() -> Settings:
    return Settings()
