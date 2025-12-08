"""Инструмент получения профиля компании по UUID."""

from __future__ import annotations

from fastmcp import Context
from mcp.shared.exceptions import ErrorData, McpError
from mcp.types import TextContent
from pydantic import Field

from db import ensure_tables, fetch_company_profile
from mcp_instance import mcp
from tools.utils import ToolResult, _require_env_vars


@mcp.tool(
    name="get_company_profile",
    description="""🔍 Возвращает профиль компании по UUID.""",
)
async def get_company_profile(
    company_id: str = Field(..., description="UUID компании"),
    ctx: Context = None,
) -> ToolResult:
    """Получает профиль компании по идентификатору.

    Args:
        company_id: UUID компании.
        ctx: Контекст MCP для логирования.

    Returns:
        ToolResult: Найденный профиль компании.

    Raises:
        McpError: Если компания не найдена.
    """

    _require_env_vars(["DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD"])

    await ctx.info("🔎 Ищем профиль компании")
    await ctx.report_progress(progress=0, total=100)

    ensure_tables()
    await ctx.report_progress(progress=25, total=100)

    try:
        profile = fetch_company_profile(company_id)
    except ValueError as exc:
        await ctx.error(f"❌ Компания с id {company_id} не найдена")

        raise McpError(
            ErrorData(code=-32601, message=f"Компания {company_id} не найдена")
        )

    await ctx.report_progress(progress=100, total=100)
    await ctx.info("✅ Профиль найден")

    return ToolResult(
        content=[
            TextContent(
                type="text",
                text=f"Компания {profile.name}: {profile.description}",
            )
        ],
        structured_content=profile.model_dump(),
        meta={"operation": "get_company_profile"},
    )
