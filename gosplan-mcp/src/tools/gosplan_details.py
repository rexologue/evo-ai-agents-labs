"""Инструмент получения деталей закупки по номеру."""

import httpx
from fastmcp import Context
from mcp.shared.exceptions import ErrorData, McpError
from mcp.types import TextContent
from opentelemetry import trace
from pydantic import Field, ValidationError

from mcp_instance import mcp
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
    """Возвращает подробности закупки по её номеру."""

    with tracer.start_as_current_span("get_purchase_details") as span:
        span.set_attribute("purchase_number", purchase_number)

        await ctx.info(f"📋 Получаем детали закупки {purchase_number}")
        await ctx.report_progress(progress=0, total=100)

        try:
            try:
                GetPurchaseDetailsRequest(purchase_number=purchase_number)
            except ValidationError as exc:
                span.set_attribute("error", "validation_error")
                await ctx.error(f"❌ Неверный номер закупки: {exc}")
                raise McpError(
                    ErrorData(
                        code=-32602, message=f"Неверный номер закупки: {exc}"
                    )
                ) from exc

            await ctx.info("🔧 Подготовка запроса")
            await ctx.report_progress(progress=25, total=100)

            await ctx.info("📡 Отправляем запрос к API ГосПлан")
            await ctx.report_progress(progress=50, total=100)

            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.get(
                    f"https://v2test.gosplan.info/fz223/purchases/{purchase_number}"
                )

                if response.status_code == 404:
                    span.set_attribute("error", "not_found")
                    await ctx.error(
                        f"❌ Закупка с номером {purchase_number} не найдена"
                    )

                    raise McpError(
                        ErrorData(
                            code=-32602,
                            message=(
                                f"Закупка с номером {purchase_number} не найдена в базе ГосПлан"
                            ),
                        )
                    )

                response.raise_for_status()
                purchase_data = response.json()

            await ctx.report_progress(progress=75, total=100)

            try:
                purchase = Purchase(**purchase_data)
            except ValidationError as exc:
                span.set_attribute("error", "parse_error")
                await ctx.error(f"❌ Ошибка парсинга ответа API: {exc}")

                raise McpError(
                    ErrorData(
                        code=-32603,
                        message=f"Ошибка обработки ответа API: {exc}",
                    )
                )

            formatted_text = format_purchase_details(purchase.model_dump())

            await ctx.report_progress(progress=100, total=100)
            await ctx.info("✅ Детали закупки получены")

            span.set_attribute("success", True)
            span.set_attribute("documents_count", len(purchase.docs))
            span.set_attribute("stage", purchase.stage)

            return ToolResult(
                content=[TextContent(type="text", text=formatted_text)],
                structured_content=purchase.model_dump(),
                meta={
                    "purchase_number": purchase_number,
                    "documents_count": len(purchase.docs),
                    "stage": purchase.stage,
                },
            )

        except httpx.HTTPStatusError as exc:
            span.set_attribute("error", "http_status_error")
            span.set_attribute("status_code", exc.response.status_code)

            error_message = format_api_error(
                exc.response.text if exc.response else "",
                exc.response.status_code if exc.response else 0,
            )

            await ctx.error(f"❌ HTTP ошибка: {error_message}")

            raise McpError(
                ErrorData(
                    code=-32603,
                    message=(
                        "Не удалось получить детали закупки.\n\n"
                        f"{error_message}"
                    ),
                )
            )

        except httpx.TimeoutException as exc:
            span.set_attribute("error", "timeout")
            await ctx.error("❌ Превышено время ожидания ответа от API")

            raise McpError(
                ErrorData(
                    code=-32603,
                    message="Превышено время ожидания ответа от API",
                )
            ) from exc

        except httpx.RequestError as exc:
            span.set_attribute("error", "request_error")
            await ctx.error(f"❌ Ошибка запроса: {exc}")

            raise McpError(
                ErrorData(
                    code=-32603, message="Не удалось выполнить запрос к API"
                ),
            ) from exc

        except Exception as exc:  # pragma: no cover - отладочная защита
            span.set_attribute("error", "unexpected_error")
            await ctx.error(f"❌ Непредвиденная ошибка: {exc}")
            raise
