"""MCP сервер для работы с профилями компаний в PostgreSQL."""

from __future__ import annotations

from config import get_settings

# CORS + ASGI
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
import uvicorn

# Единый экземпляр FastMCP
from mcp_instance import mcp

settings = get_settings()

# Импортируем инструменты (как и раньше)
print("🔧 Загружаем инструменты...")
try:
    from tools.get_okdp2_codes import get_okpd2_codes
    print("✅ get_okpd2_codes загружен")
except Exception as e:
    print(f"❌ Ошибка импорта get_okpd2_codes: {e}")
    import traceback
    traceback.print_exc()

try:
    from tools.get_regions_codes import get_regions_codes
    print("✅ get_regions_codes загружен")
except Exception as e:
    print(f"❌ Ошибка импорта get_regions_codes: {e}")
    import traceback
    traceback.print_exc()


# --- CORS middleware специально для MCP Inspector ---

middleware = [
    Middleware(
        CORSMiddleware,
        allow_origins=["*"],  # для разработки; в проде лучше указать конкретный origin
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

# ASGI-приложение FastMCP c CORS
app = mcp.http_app(middleware=middleware)  # по умолчанию путь /mcp


def main():
    """Запуск MCP сервера с HTTP транспортом и CORS."""
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
    except KeyboardInterrupt:
        print("\n🛑 Получен сигнал остановки (Ctrl+C)")
        print("🔄 Выполняем graceful shutdown...")
        print("✅ Сервер остановлен")
    except Exception as e:
        print(f"❌ Ошибка запуска сервера: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
