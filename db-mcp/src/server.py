"""MCP сервер для работы с профилями компаний в PostgreSQL."""

from __future__ import annotations

import os

from dotenv import find_dotenv, load_dotenv
from opentelemetry import trace

from .db import ensure_tables
from .mcp_instance import mcp
from .tools.create_company_profile import create_company_profile
from .tools.get_company_profile import get_company_profile
from .tools.list_company_profiles import list_company_profiles

# Загрузка переменных окружения
load_dotenv(find_dotenv())

PORT = int(os.getenv("PORT", "8000"))
HOST = os.getenv("HOST", "0.0.0.0")

tracer = trace.get_tracer(__name__)


def init_tracing() -> None:
    """Инициализация OpenTelemetry (заглушка для расширения)."""

    with tracer.start_as_current_span("init_tracing"):
        pass


init_tracing()


@mcp.prompt()
def healthcheck_prompt() -> str:
    """Промпт-заглушка для проверки регистрации MCP."""

    return "db-mcp healthcheck"


def main() -> None:
    """Запуск MCP сервера с HTTP транспортом."""

    print("=" * 60)
    print("🌐 ЗАПУСК MCP СЕРВЕРА db-mcp")
    print("=" * 60)
    print(f"🚀 MCP Server: http://{HOST}:{PORT}/mcp")
    print("=" * 60)

    ensure_tables()
    mcp.run(transport="streamable-http", host=HOST, port=PORT, stateless_http=True)


if __name__ == "__main__":
    main()
