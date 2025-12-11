"""Инструмент создания профиля компании в БД."""

from __future__ import annotations

from fastmcp import Context
from mcp.shared.exceptions import ErrorData, McpError
from mcp.types import TextContent
from pydantic import Field

from db import ensure_tables, insert_company_profile
from mcp_instance import mcp
from models import CompanyProfileBase
from tools.utils import ToolResult, _require_env_vars


@mcp.tool(
    name="create_company_profile",
    description="""📝 Создает новый профиль компании и сохраняет его в PostgreSQL.""",
)
async def create_company_profile(
    profile: CompanyProfileBase | None = Field(
        default=None, description="Структурированный профиль компании для сохранения"
    ),
    ctx: Context = None,
) -> ToolResult:
    """Создает профиль компании и возвращает сохраненную запись.

    Args:
        profile: Описание компании со всеми полями.
        ctx: Контекст MCP для логирования и прогресса.

    Returns:
        ToolResult: Сохраненный профиль компании.
    """

    if profile is None:
        await ctx.error("❌ Не передан профиль компании")

        raise McpError(
            ErrorData(
                code=-32602,
                message="Параметр 'profile' обязателен для create_company_profile",
            )
        )

    _require_env_vars(["DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD"])

    await ctx.info("🚀 Создаем профиль компании")
    await ctx.report_progress(progress=0, total=100)

    ensure_tables()
    await ctx.info("🔧 Проверили схему БД")
    await ctx.report_progress(progress=25, total=100)

    saved_profile = insert_company_profile(profile)
    await ctx.report_progress(progress=75, total=100)
    await ctx.info("✅ Профиль успешно сохранен")

    await ctx.report_progress(progress=100, total=100)

    return ToolResult(
        content=[
            TextContent(
                type="text",
                text=f"Профиль компании {saved_profile.name} сохранен с id {saved_profile.id}",
            )
        ],
        structured_content=saved_profile.model_dump(),
        meta={"operation": "create_company_profile"},
    )
