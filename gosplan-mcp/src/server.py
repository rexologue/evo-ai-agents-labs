"""MCP сервер для финансовых расчетов с HTTP транспортом."""

from src.mcp_instance import mcp
from src.utils.settings import settings

import fastmcp
fastmcp.settings.port = settings.app.port
fastmcp.settings.host = settings.app.host

# Импортируем инструменты
print("🔧 Загружаем инструменты...")
try:
    from src.tools.gosplan_search import search_purchases

    print("✅ search_purchases загружен")
except Exception as e:
    print(f"❌ Ошибка импорта search_purchases: {e}")
    import traceback

    traceback.print_exc()

try:
    from src.tools.gosplan_details import get_purchase_details

    print("✅ get_purchase_details загружен")
except Exception as e:
    print(f"❌ Ошибка импорта get_purchase_details: {e}")
    import traceback

    traceback.print_exc()

print("✅ Все инструменты загружены:")
print("  - search_purchases (поиск государственных закупок)")
print("  - get_purchase_details (детали государственной закупки)")


def main():
    """Запуск MCP сервера с HTTP транспортом."""
    print("=" * 60)
    print("🌐 ЗАПУСК MCP СЕРВЕРА")
    print("=" * 60)
    print(f"🚀 MCP Server: http://{settings.app.host}:{settings.app.port}/mcp")
    print(f"📊 Метрики: http://{settings.app.host}:{settings.app.port}/metrics")
    print(f"🏥 Health check: http://{settings.app.host}:{settings.app.port}/health")
    print("🔧 Используйте MCP Inspector для подключения к серверу")
    print("=" * 60)
    print("⏳ Запускаем сервер...")

    # Запускаем MCP сервер с streamable-http транспортом
    try:
        mcp.run(
            transport="streamable-http",
            host=settings.app.host,
            port=settings.app.port
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
