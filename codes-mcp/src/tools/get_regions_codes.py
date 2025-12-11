"""Инструмент получения таблицы кодов регионов"""

from __future__ import annotations

from fastmcp import Context
from mcp.types import TextContent
from pydantic import Field

from mcp_instance import mcp
from tools.utils import format_region_index, to_dict_region_index, REGION_INDEX, ToolResult


@mcp.tool(
    name="get_regions_codes",
    description="Выдает таблицу кодов и соответствующих им названий регионов",
)
async def get_regions_codes(
    ctx: Context = None,
    query: str = Field(
        default="",
        description="Часть названия региона или код (для контекстного поиска, опционально)",
    ),
) -> ToolResult:
    normalized_query = query.strip().lower()
    regions = [
        region
        for region in REGION_INDEX
        if not normalized_query
        or normalized_query in region.title.lower()
        or normalized_query in region.code.lower()
    ]

    if ctx:
        await ctx.info(
            "Формируем таблицу кодов регионов" if not query else f"Формируем таблицу кодов регионов (запрос: {query})"
        )
        await ctx.report_progress(progress=0, total=50)

    regions_table = format_region_index(regions)

    if ctx:
        await ctx.report_progress(progress=50, total=100)
        await ctx.info("Таблица успешно сформирована")
        await ctx.report_progress(progress=100, total=100)

    return ToolResult(
        content=[TextContent(type="text", text=regions_table)],
        structured_content=to_dict_region_index(regions),
        meta={
            "operation": "get_regions_codes",
            "count": len(regions),
            "query": query,
        },
    )
