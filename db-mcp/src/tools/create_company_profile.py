"""Инструмент создания профиля компании в БД."""

from __future__ import annotations

from fastmcp import Context
from mcp.types import TextContent
from pydantic import Field

from db import ensure_tables, insert_company_profile
from mcp_instance import mcp
from models import CompanyProfileBase
from tools.utils import ToolResult, _require_env_vars


@mcp.tool(
    name="create_company_profile",
    description="📝 Создает новый профиль компании и сохраняет его в PostgreSQL.",
)
async def create_company_profile(
    ctx: Context,
    profile: CompanyProfileBase = Field(
        ..., description="Структурированный профиль компании для сохранения"
    ),
) -> ToolResult:
    _require_env_vars(["DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD"])
    
    if profile is None:
        await ctx.info("❌ Профиль не передан в аргументах")
        return ToolResult(
            content=[
                TextContent(
                    type="text",
                    text="Ошибка: не передан аргумент 'profile' при вызове инструмента create_company_profile.",
                )
            ],
            structured_content=None,
            meta={"operation": "create_company_profile", "error": "missing_profile"},
        )

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

