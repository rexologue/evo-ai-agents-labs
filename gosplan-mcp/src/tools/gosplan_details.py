"""Инструмент получения деталей закупки по номеру."""

from __future__ import annotations

from typing import Literal

import httpx
from fastmcp import Context
from mcp.shared.exceptions import ErrorData, McpError
from mcp.types import TextContent
from opentelemetry import trace
from pydantic import Field

from mcp_instance import mcp
from .models import LawLiteral, PurchaseFeatures
from .utils import (
    ToolResult,
    build_purchase_features,
    create_http_client,
    format_api_error,
    format_purchase_details,
)

tracer = trace.get_tracer(__name__)

LAW_PATHS: dict[LawLiteral, str] = {
    "44-FZ": "fz44",
    "223-FZ": "fz223",
}


@mcp.tool(
    name="get_purchase_details",
    description=(
        "📋 Детальная информация о закупке по номеру для 44-ФЗ и 223-ФЗ"
    ),
)
async def get_purchase_details(
    ctx: Context,
    purchase_number: str = Field(..., description="Номер закупки"),
    law: Literal["AUTO", LawLiteral] = Field(
        "AUTO", description="Явно указать закон или выбрать автоматически."
    ),
) -> ToolResult:
    """Возвращает подробности закупки по её номеру."""

    with tracer.start_as_current_span("get_purchase_details") as span:
        span.set_attribute("purchase_number", purchase_number)

        await ctx.info(f"📋 Получаем детали закупки {purchase_number}")
        await ctx.report_progress(progress=0, total=100)

        if not purchase_number:
            span.set_attribute("error", "validation_error")
            message = "Пустой номер закупки"
            await ctx.error(message)
            raise McpError(ErrorData(code=-32602, message=message))

        await ctx.report_progress(progress=20, total=100)

        laws_chain: list[LawLiteral]
        if law == "AUTO":
            laws_chain = ["44-FZ", "223-FZ"] if len(purchase_number) > 15 else ["223-FZ", "44-FZ"]
        else:
            laws_chain = [law]

        last_error: Exception | None = None
        purchase: PurchaseFeatures | None = None

        async with create_http_client() as client:
            for current_law in laws_chain:
                path = f"/{LAW_PATHS[current_law]}/purchases/{purchase_number}"
                try:
                    response = await client.get(path)
                    if response.status_code == 404:
                        continue
                    response.raise_for_status()
                    purchase = build_purchase_features(response.json(), current_law)
                    break
                except httpx.HTTPStatusError as exc:
                    last_error = exc
                    if exc.response is not None and exc.response.status_code == 404:
                        continue
                    span.set_attribute("error", "http_status_error")
                    error_message = format_api_error(
                        exc.response.text if exc.response else "",
                        exc.response.status_code if exc.response else 0,
                    )
                    await ctx.error(f"❌ HTTP ошибка: {error_message}")
                    raise McpError(
                        ErrorData(
                            code=-32603,
                            message=(
                                "Не удалось получить детали закупки.\n\n" f"{error_message}"
                            ),
                        )
                    ) from exc
                except httpx.RequestError as exc:
                    last_error = exc
                    span.set_attribute("error", "request_error")
                    await ctx.error(f"❌ Ошибка запроса: {exc}")
                    raise McpError(
                        ErrorData(
                            code=-32603, message="Не удалось выполнить запрос к API"
                        ),
                    ) from exc

        if purchase is None:
            await ctx.error("❌ Закупка не найдена ни по 44-ФЗ, ни по 223-ФЗ")
            raise McpError(
                ErrorData(
                    code=-32602,
                    message=(
                        "Закупка с указанным номером не найдена в ГосПлан (44-ФЗ/223-ФЗ)."
                    ),
                )
            ) from last_error

        await ctx.report_progress(progress=80, total=100)
        formatted_text = format_purchase_details(purchase)

        await ctx.report_progress(progress=100, total=100)
        span.set_attribute("success", True)
        span.set_attribute("law", purchase.law)

        return ToolResult(
            content=[TextContent(type="text", text=formatted_text)],
            structured_content=purchase.model_dump(),
            meta={
                "purchase_number": purchase.purchase_number,
                "law": purchase.law,
            },
        )
