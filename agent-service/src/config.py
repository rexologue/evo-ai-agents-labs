from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    llm_model: str = Field(default="gpt-4o-mini", alias="LLM_MODEL")
    llm_api_key: str = Field(alias="LLM_API_KEY")
    llm_api_base: str = Field(default="https://api.openai.com/v1", alias="LLM_API_BASE")
    db_mcp_url: str = Field(default="http://localhost:8000", alias="DB_MCP_URL")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


def get_settings() -> Settings:
    return Settings()
