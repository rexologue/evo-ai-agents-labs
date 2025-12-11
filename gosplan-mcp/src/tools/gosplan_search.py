"""Инструмент поиска государственных закупок по 44-ФЗ и 223-ФЗ."""

from __future__ import annotations

from datetime import datetime
from typing import Iterable, List, Literal

import httpx
from fastmcp import Context
from mcp.shared.exceptions import ErrorData, McpError
from mcp.types import TextContent
from pydantic import Field, ValidationError

from config import get_settings
from mcp_instance import mcp
from models import LawLiteral, PurchaseListItem, SearchPurchasesParams
from tools.utils import (
    ToolResult,
    create_http_client,
    filter_and_slice_results,
    format_api_error,
    format_purchase_list,
    parse_datetime,
)


LAW_PATHS: dict[LawLiteral, str] = {
    "44-FZ": "fz44",
    "223-FZ": "fz223",
}


def _prepare_query(params: SearchPurchasesParams, limit: int) -> dict:
    query: dict[str, str | int] = {"limit": limit}
    if params.okpd2_codes:
        query["okpd2"] = ",".join(params.okpd2_codes)
    if params.region_codes:
        query["region"] = ",".join(str(code) for code in params.region_codes)
    if params.applications_end_before:
        query["submission_close_before"] = params.applications_end_before.isoformat()
    return query


def _sort_purchases(items: Iterable[PurchaseListItem]) -> List[PurchaseListItem]:
    return sorted(
        items,
        key=lambda item: (
            item.submission_close_at or datetime.max,
            item.published_at if hasattr(item, "published_at") else datetime.max,
        ),
    )


@mcp.tool(
    name="search_purchases",
    description=(
        "🔍 Поиск закупок по кодам ОКПД2, регионам и дедлайну подачи заявок."
        " Работает по 44-ФЗ и 223-ФЗ, возвращает до 9 свежих закупок."
    ),
)
async def search_purchases(
    ctx: Context,
    okpd2_codes: List[str] = Field(
        default_factory=list, description="Список кодов ОКПД2 (можно передать несколько)."
    ),
    region_codes: List[int] = Field(
        default_factory=list, description="Коды регионов, пусто — все регионы."
    ),
    applications_end_before: str | None = Field(
        None,
        description="ISO-дата/дата-время: исключить закупки с дедлайном позже указанной даты.",
    ),
    law: Literal["ALL", LawLiteral] = Field(
        "ALL", description="Искать по 44-ФЗ, 223-ФЗ или по обоим сразу."
    ),
) -> ToolResult:
    """Поиск государственных закупок по входным параметрам."""

    await ctx.info("🔍 Начинаем поиск государственных закупок")
    await ctx.report_progress(progress=0, total=100)

    settings = get_settings()
    try:
        end_dt = parse_datetime(applications_end_before)
        params = SearchPurchasesParams(
            okpd2_codes=okpd2_codes,
            region_codes=region_codes,
            applications_end_before=end_dt,
            law=law,
            limit=settings.purchases_limit,
        )
        
    except ValidationError as exc:
        await ctx.error(f"❌ Неверные параметры: {exc}")
        raise McpError(
            ErrorData(code=-32602, message=f"Неверные параметры: {exc}")
        ) from exc

    await ctx.report_progress(progress=15, total=100)

    laws_to_query: list[LawLiteral] = (
        ["44-FZ", "223-FZ"] if params.law == "ALL" else [params.law]
    )
    collected: list[PurchaseListItem] = []

    async with create_http_client() as client:
        for current_law in laws_to_query:
            if len(collected) >= params.limit:
                break

            limit_left = params.limit - len(collected)
            query_params = _prepare_query(params, limit_left)
            path = f"/{LAW_PATHS[current_law]}/purchases"

            try:
                response = await client.get(path, params=query_params)
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                error_message = format_api_error(
                    exc.response.text if exc.response else "",
                    exc.response.status_code if exc.response else 0,
                )
                await ctx.error(f"❌ HTTP ошибка: {error_message}")
                raise McpError(
                    ErrorData(
                        code=-32603,
                        message=f"Не удалось получить список закупок.\n\n{error_message}",
                    )
                ) from exc
                
            except httpx.RequestError as exc:
                await ctx.error(f"❌ Ошибка запроса: {exc}")
                raise McpError(
                    ErrorData(
                        code=-32603,
                        message="Не удалось выполнить запрос к API",
                    )
                ) from exc

            batch = [
                PurchaseListItem(law=current_law, **item)
                for item in response.json()
            ]
            collected.extend(batch)

    await ctx.report_progress(progress=70, total=100)

    filtered = filter_and_slice_results(
        _sort_purchases(collected),
        params,
    )

    await ctx.report_progress(progress=90, total=100)
    formatted_text = format_purchase_list(filtered)

    await ctx.report_progress(progress=100, total=100)

    return ToolResult(
        content=[TextContent(type="text", text=formatted_text)],
        structured_content=[item.model_dump() for item in filtered],
        meta={"count": len(filtered)},
    )
