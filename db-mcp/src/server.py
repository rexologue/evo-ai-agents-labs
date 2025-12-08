"""MCP сервер для работы с профилями компаний в PostgreSQL."""

from __future__ import annotations

from opentelemetry import trace

from .config import get_settings
from .db import ensure_tables
from .mcp_instance import mcp
from .tools.create_company_profile import create_company_profile
from .tools.get_company_profile import get_company_profile
from .tools.list_company_profiles import list_company_profiles

settings = get_settings()

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
    print(
        "🚀 MCP Server: "
        f"http://{settings.server_host}:{settings.server_port}/mcp"
    )
    print("=" * 60)

    ensure_tables()
    mcp.run(
        transport="streamable-http",
        host=settings.server_host,
        port=settings.server_port,
        stateless_http=True,
    )


if __name__ == "__main__":
    main()
