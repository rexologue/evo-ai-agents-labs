"""Инструмент получения таблицы ОКПД2 кодов"""

from __future__ import annotations

from fastmcp import Context
from mcp.types import TextContent
from pydantic import Field

from mcp_instance import mcp
from tools.utils import format_okpd2_index, OKPD2_INDEX, ToolResult


@mcp.tool(
    name="get_okpd2_codes",
    description="Выдает таблицу кодов и соответствующих им наименований по ОКПД2.",
)
async def get_okpd2_codes(ctx: Context = None) -> ToolResult:

    if ctx:
        await ctx.info("Формируем таблицу кодов ОКПД2")
        await ctx.report_progress(progress=0, total=50)

    okpd2_table = format_okpd2_index()

    if ctx:
        await ctx.report_progress(progress=50, total=100)
        await ctx.info("Таблица успешно сформирована")
        await ctx.report_progress(progress=100, total=100)

    return ToolResult(
        content=[TextContent(type="text", text=okpd2_table)],
        structured_content=OKPD2_INDEX,
        meta={
            "operation": "get_okpd2_codes",
            "count": len(OKPD2_INDEX),
        },
    )