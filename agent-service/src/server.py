"""MCP сервер для запуска профильного агента."""

from __future__ import annotations

from opentelemetry import trace

from .config import get_settings
from .mcp_instance import mcp
from .tools.generate_company_profile import generate_company_profile

settings = get_settings()

tracer = trace.get_tracer(__name__)


def init_tracing() -> None:
    """Инициализация OpenTelemetry (расширяется при необходимости)."""

    with tracer.start_as_current_span("init_tracing"):
        pass


init_tracing()


@mcp.prompt()
def profile_prompt(description: str = "") -> str:
    """Промпт-заглушка для совместимости с MCP."""

    return f"Профильное описание: {description}"


def main() -> None:
    """Запуск MCP сервера с HTTP транспортом."""

    print("=" * 60)
    print("🌐 ЗАПУСК MCP СЕРВЕРА agent-service")
    print("=" * 60)
    print(f"🚀 MCP Server: http://{settings.agent_host}:{settings.agent_port}/mcp")
    print("=" * 60)

    mcp.run(
        transport="streamable-http",
        host=settings.agent_host,
        port=settings.agent_port,
        stateless_http=True,
    )


if __name__ == "__main__":
    main()
