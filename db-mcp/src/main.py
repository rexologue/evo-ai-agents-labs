"""MCP сервер для работы с профилями компаний."""
from __future__ import annotations

import os
from typing import Optional

from dotenv import load_dotenv, find_dotenv
from fastmcp import FastMCP, tool

from .config import get_settings
from .models import CompanyProfileBase, CompanyProfileDB
from .utils import ensure_tables, fetch_company_profile, fetch_company_profiles, insert_company_profile

load_dotenv(find_dotenv())
settings = get_settings()

mcp = FastMCP("db-mcp", version="0.1.0", description="PostgreSQL-backed MCP for company profiles")


@tool
async def create_company_profile(profile: CompanyProfileBase) -> CompanyProfileDB:
    """Создает профиль компании в БД и возвращает сохраненную запись."""
    ensure_tables()
    return insert_company_profile(profile)


@tool
async def get_company_profile(company_id: str) -> CompanyProfileDB:
    """Возвращает профиль компании по UUID."""
    ensure_tables()
    return fetch_company_profile(company_id)


@tool
async def list_company_profiles(
    query: Optional[str] = None, limit: int = 20, offset: int = 0
) -> list[CompanyProfileDB]:
    """Список профилей компаний c необязательным поиском по имени и описанию."""
    ensure_tables()
    return fetch_company_profiles(query, limit, offset)


# Регистрируем инструменты
mcp.register_tool(create_company_profile)
mcp.register_tool(get_company_profile)
mcp.register_tool(list_company_profiles)


def main():
    port = int(os.getenv("PORT", settings.port))
    print(f"🚀 Запускаем db-mcp на порту {port}")
    ensure_tables()
    mcp.run(transport="streamable-http", host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
