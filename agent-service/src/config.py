from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    llm_model: str = Field(..., alias="LLM_MODEL")
    llm_api_key: str = Field(..., alias="LLM_API_KEY")
    llm_api_base: str = Field(..., alias="LLM_API_BASE")
    db_mcp_url: str = Field(..., alias="DB_MCP_URL")
    agent_host: str = Field(..., alias="AGENT_HOST")
    agent_port: int = Field(..., alias="AGENT_PORT")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


def get_settings() -> Settings:
    return Settings()
