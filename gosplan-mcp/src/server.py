"""MCP сервер для работы с данными ГосПлан по HTTP."""

from __future__ import annotations

import uvicorn
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

from config import get_settings
from mcp_instance import mcp

settings = get_settings()

print("🔧 Загружаем инструменты...")
try:
    from tools.gosplan_search import search_purchases
    print("✅ search_purchases загружен")
except Exception as exc:  # pragma: no cover - отладочное сообщение
    print(f"❌ Ошибка импорта search_purchases: {exc}")
    import traceback

    traceback.print_exc()

try:
    from tools.gosplan_details import get_purchase_details
    print("✅ get_purchase_details загружен")
except Exception as exc:  # pragma: no cover - отладочное сообщение
    print(f"❌ Ошибка импорта get_purchase_details: {exc}")
    import traceback

    traceback.print_exc()

middleware = [
    Middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=[
            "mcp-protocol-version",
            "mcp-session-id",
            "Authorization",
            "Content-Type",
        ],
        expose_headers=["mcp-session-id"],
    )
]

app = mcp.http_app(middleware=middleware)


def main() -> None:
    """Запускает MCP сервер с HTTP транспортом и CORS."""

    print("=" * 60)
    print("🌐 ЗАПУСК MCP СЕРВЕРА (HTTP + CORS)")
    print("=" * 60)
    print(f"🚀 MCP Server: http://{settings.server_host}:{settings.server_port}/mcp")
    print(f"📊 Метрики:    http://{settings.server_host}:{settings.server_port}/metrics")
    print(f"🏥 Health:     http://{settings.server_host}:{settings.server_port}/health")
    print("🔧 Используйте MCP Inspector (Connection Type: Direct)")
    print("=" * 60)
    print("⏳ Запускаем Uvicorn...")

    try:
        uvicorn.run(
            app,
            host=settings.server_host,
            port=settings.server_port,
        )
    except KeyboardInterrupt:  # pragma: no cover - остановка через Ctrl+C
        print("\n🛑 Получен сигнал остановки (Ctrl+C)")
        print("🔄 Выполняем graceful shutdown...")
        print("✅ Сервер остановлен")
    except Exception as exc:  # pragma: no cover - отладочное сообщение
        print(f"❌ Ошибка запуска сервера: {exc}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
