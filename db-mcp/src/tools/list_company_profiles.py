"""Инструмент получения списка профилей компаний."""

from __future__ import annotations

from fastmcp import Context
from mcp.types import TextContent
from pydantic import Field

from db import ensure_tables, fetch_company_profiles
from mcp_instance import mcp
from tools.utils import ToolResult, _require_env_vars


@mcp.tool(
    name="list_company_profiles",
    description="""📄 Список профилей компаний с поиском и пагинацией.""",
)
async def list_company_profiles(
    query: str | None = Field(
        default=None, description="Опциональный поисковый запрос по имени или описанию"
    ),
    limit: int = Field(default=20, description="Количество записей в выдаче"),
    offset: int = Field(default=0, description="Смещение для пагинации"),
    ctx: Context = None,
) -> ToolResult:
    """Возвращает список профилей компаний.

    Args:
        query: Строка поиска по имени или описанию.
        limit: Количество элементов.
        offset: Смещение выдачи.
        ctx: Контекст MCP.

    Returns:
        ToolResult: Список профилей компаний.
    """

    _require_env_vars(["DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD"])

    await ctx.info("📑 Получаем список профилей компаний")
    await ctx.report_progress(progress=0, total=100)

    ensure_tables()
    await ctx.report_progress(progress=25, total=100)

    profiles = fetch_company_profiles(query, limit, offset)
    await ctx.report_progress(progress=100, total=100)
    await ctx.info(f"✅ Найдено профилей: {len(profiles)}")

    formatted = "\n".join([f"- {profile.name}" for profile in profiles]) or "Нет записей"

    return ToolResult(
        content=[TextContent(type="text", text=formatted)],
        structured_content={"items": [p.model_dump() for p in profiles]},
        meta={"operation": "list_company_profiles"},
    )
