"""Инструмент для получения детальной информации о государственной закупке."""

import httpx
from fastmcp import Context
from mcp.shared.exceptions import ErrorData, McpError
from mcp.types import TextContent
from opentelemetry import trace
from pydantic import Field, ValidationError

from ..mcp_instance import mcp
from ..metrics import API_CALLS

from .models import GetPurchaseDetailsRequest, Purchase
from .utils import ToolResult, format_api_error, format_purchase_details

tracer = trace.get_tracer(__name__)


@mcp.tool(
    name="get_purchase_details",
    description="""📋 Получение детальной информации о государственной закупке

Получает полную информацию о конкретной закупке по её номеру, включая:
- Полное описание предмета закупки
- Все документы с оригинальными данными
- Места поставки
- Связанные планы закупок

Параметры:
- purchase_number: Номер закупки (обязательный)
""",
)
async def get_purchase_details(
    ctx: Context,
    purchase_number: str = Field(..., description="Номер закупки"),
) -> ToolResult:
    """
    Получение детальной информации о государственной закупке.

    Args:
        purchase_number: Номер закупки
        ctx: Контекст для логирования

    Returns:
        ToolResult: Детальная информация о закупке

    Raises:
        McpError: При ошибках выполнения
    """
    with tracer.start_as_current_span("get_purchase_details") as span:
        span.set_attribute("purchase_number", purchase_number)

        await ctx.info(f"📋 Получаем детали закупки {purchase_number}")
        await ctx.report_progress(progress=0, total=100)

        API_CALLS.labels(
            service="gosplan",
            endpoint="get_purchase_details",
            status="started",
        ).inc()

        try:
            # Этап 1: Валидация (0-25%)
            try:
                GetPurchaseDetailsRequest(purchase_number=purchase_number)
            except ValidationError as e:
                span.set_attribute("error", "validation_error")
                await ctx.error(f"❌ Неверный номер закупки: {e}")
                raise McpError(
                    ErrorData(
                        code=-32602, message=f"Неверный номер закупки: {e}"
                    )
                ) from e

            await ctx.info("🔧 Подготовка запроса")
            await ctx.report_progress(progress=25, total=100)

            # Этап 2: Выполнение запроса к API (25-75%)
            await ctx.info("📡 Отправляем запрос к API ГосПлан")
            await ctx.report_progress(progress=50, total=100)

            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.get(
                    f"https://v2test.gosplan.info/fz223/purchases/"
                    f"{purchase_number}"
                )

                # Специальная обработка 404
                if response.status_code == 404:
                    span.set_attribute("error", "not_found")
                    await ctx.error(
                        f"❌ Закупка с номером {purchase_number} не найдена"
                    )

                    API_CALLS.labels(
                        service="gosplan",
                        endpoint="get_purchase_details",
                        status="error",
                    ).inc()

                    raise McpError(
                        ErrorData(
                            code=-32602,
                            message=f"Закупка с номером {purchase_number} "
                            f"не найдена в базе ГосПлан",
                        )
                    )

                response.raise_for_status()
                purchase_data = response.json()

            await ctx.report_progress(progress=75, total=100)

            # Этап 3: Обработка результатов (75-100%)
            await ctx.info("📄 Обрабатываем детали закупки")

            # Парсим с использованием Pydantic
            try:
                purchase = Purchase(**purchase_data)
            except ValidationError as e:
                span.set_attribute("error", "parse_error")
                await ctx.error(f"❌ Ошибка парсинга ответа API: {e}")

                API_CALLS.labels(
                    service="gosplan",
                    endpoint="get_purchase_details",
                    status="error",
                ).inc()

                raise McpError(
                    ErrorData(
                        code=-32603,
                        message=f"Ошибка обработки ответа API: {e}",
                    )
                )

            # Форматируем детальное представление
            formatted_text = format_purchase_details(purchase.model_dump())

            await ctx.report_progress(progress=100, total=100)
            await ctx.info("✅ Детали закупки получены")

            span.set_attribute("success", True)
            span.set_attribute("documents_count", len(purchase.docs))
            span.set_attribute("stage", purchase.stage)

            API_CALLS.labels(
                service="gosplan",
                endpoint="get_purchase_details",
                status="success",
            ).inc()

            return ToolResult(
                content=[TextContent(type="text", text=formatted_text)],
                structured_content=purchase.model_dump(),
                meta={
                    "purchase_number": purchase_number,
                    "documents_count": len(purchase.docs),
                    "stage": purchase.stage,
                },
            )

        except httpx.HTTPStatusError as e:
            # 404 обработан выше, остальные HTTP ошибки здесь
            span.set_attribute("error", "http_status_error")
            span.set_attribute("status_code", e.response.status_code)

            error_message = format_api_error(
                e.response.text if e.response else "",
                e.response.status_code if e.response else 0,
            )

            await ctx.error(f"❌ HTTP ошибка: {error_message}")

            API_CALLS.labels(
                service="gosplan",
                endpoint="get_purchase_details",
                status="error",
            ).inc()

            raise McpError(
                ErrorData(
                    code=-32603,
                    message=f"Не удалось получить детали закупки.\n\n"
                    f"{error_message}",
                )
            )

        except httpx.TimeoutException:
            span.set_attribute("error", "timeout")
            await ctx.error("❌ Превышено время ожидания ответа от API")

            API_CALLS.labels(
                service="gosplan",
                endpoint="get_purchase_details",
                status="error",
            ).inc()

            raise McpError(
                ErrorData(
                    code=-32603,
                    message="Превышено время ожидания ответа от API ГосПлан",
                )
            )

        except httpx.RequestError as e:
            span.set_attribute("error", "request_error")
            await ctx.error(f"❌ Ошибка сети: {e}")

            API_CALLS.labels(
                service="gosplan",
                endpoint="get_purchase_details",
                status="error",
            ).inc()

            raise McpError(
                ErrorData(
                    code=-32603,
                    message=f"Ошибка подключения к API ГосПлан: {e}",
                )
            )

        except Exception as e:
            span.set_attribute("error", str(e))
            await ctx.error(f"💥 Неожиданная ошибка: {e}")

            API_CALLS.labels(
                service="gosplan",
                endpoint="get_purchase_details",
                status="error",
            ).inc()

            raise McpError(
                ErrorData(code=-32603, message=f"Неожиданная ошибка: {e}")
            )
