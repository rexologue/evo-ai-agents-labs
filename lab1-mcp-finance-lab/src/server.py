"""MCP сервер для финансовых расчетов с HTTP транспортом."""

# Standard library
import os

# Third-party
from dotenv import load_dotenv, find_dotenv

# Load environment variables
load_dotenv(find_dotenv())

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter as OTLPHTTPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
OPENTELEMETRY_AVAILABLE = True

# Constants
PORT = int(os.getenv("PORT", "8000"))

# Импортируем единый экземпляр FastMCP
from mcp_instance import mcp

# Используем глобальные настройки вместо deprecated mcp.settings
import fastmcp
fastmcp.settings.port = PORT
fastmcp.settings.host = "0.0.0.0"

"""Инициализация OpenTelemetry для трейсинга.

Если задан OTEL_ENDPOINT, настраивается OTLP экспорт через OpenTelemetry SDK.
"""
def init_tracing():
    """Инициализация чистого OpenTelemetry для трейсинга."""
    if not OPENTELEMETRY_AVAILABLE:
        print("⚠️ OpenTelemetry недоступен, пропускаем инициализацию")
        return
        
    try:
        # Получаем настройки из переменных окружения
        otel_endpoint = os.getenv("OTEL_ENDPOINT", "").strip()
        otel_service_name = os.getenv("OTEL_SERVICE_NAME", "mcp-finance-server")
        
        # Настраиваем OpenTelemetry
        tracer_provider = TracerProvider(
            resource=Resource.create({
                "service.name": otel_service_name,
                "service.version": "1.0.0",
            })
        )
        
        if otel_endpoint:
            # Если есть OTLP endpoint, используем его
            if otel_endpoint.startswith("http"):
                otlp_exporter = OTLPHTTPSpanExporter(endpoint=otel_endpoint)
            else:
                from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
                otlp_exporter = OTLPSpanExporter(endpoint=otel_endpoint)
            
            span_processor = BatchSpanProcessor(otlp_exporter)
            tracer_provider.add_span_processor(span_processor)
            print(f"✅ OpenTelemetry настроен для OTLP экспорта: {otel_endpoint}")
        else:
            # Используем консольный экспортер для локальной разработки
            from opentelemetry.sdk.trace.export import ConsoleSpanExporter
            console_exporter = ConsoleSpanExporter()
            span_processor = BatchSpanProcessor(console_exporter)
            tracer_provider.add_span_processor(span_processor)
            print("✅ OpenTelemetry настроен для консольного вывода")
        
        # Устанавливаем tracer provider
        trace.set_tracer_provider(tracer_provider)
        
        print("✅ OpenTelemetry инициализирован")
        
    except Exception as e:
        print(f"⚠️ Не удалось инициализировать OpenTelemetry: {e}")
        print("ℹ️ Продолжаем работу без трейсинга")

# Инициализируем трейсинг при импорте модуля
init_tracing()

# Импортируем инструменты
print("🔧 Загружаем инструменты...")
try:
    from tools.loan_schedule_annuity import loan_schedule_annuity
    print("✅ loan_schedule_annuity загружен")
except Exception as e:
    print(f"❌ Ошибка импорта loan_schedule_annuity: {e}")
    import traceback
    traceback.print_exc()

try:
    from tools.loan_schedule_differential import loan_schedule_differential
    print("✅ loan_schedule_differential загружен")
except Exception as e:
    print(f"❌ Ошибка импорта loan_schedule_differential: {e}")
    import traceback
    traceback.print_exc()

try:
    from tools.deposit_schedule_compound import deposit_schedule_compound
    print("✅ deposit_schedule_compound загружен")
except Exception as e:
    print(f"❌ Ошибка импорта deposit_schedule_compound: {e}")
    import traceback
    traceback.print_exc()

try:
    from tools.compare_loan_schedules import compare_loan_schedules
    print("✅ compare_loan_schedules загружен")
except Exception as e:
    print(f"❌ Ошибка импорта compare_loan_schedules: {e}")
    import traceback
    traceback.print_exc()

try:
    from tools.investment_calculator import investment_calculator
    print("✅ investment_calculator загружен")
except Exception as e:
    print(f"❌ Ошибка импорта investment_calculator: {e}")
    import traceback
    traceback.print_exc()

print("✅ Все инструменты загружены:")
print("  - loan_schedule_annuity (аннуитетный кредит)")
print("  - loan_schedule_differential (дифференцированный кредит)")
print("  - deposit_schedule_compound (вклад с капитализацией)")
print("  - compare_loan_schedules (сравнение кредитов)")
print("  - investment_calculator (калькулятор инвестиций)")


def main():
    """Запуск MCP сервера с HTTP транспортом."""
    print("=" * 60)
    print("🌐 ЗАПУСК MCP СЕРВЕРА")
    print("=" * 60)
    print(f"🚀 MCP Server: http://0.0.0.0:{PORT}/mcp")
    print(f"📊 Метрики: http://0.0.0.0:{PORT}/metrics")
    print(f"🏥 Health check: http://0.0.0.0:{PORT}/health")
    print("🔧 Используйте MCP Inspector для подключения к серверу")
    print("=" * 60)
    print("⏳ Запускаем сервер...")

    # Запускаем MCP сервер с streamable-http транспортом
    try:
        mcp.run(transport="streamable-http", host="0.0.0.0", port=PORT)
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
