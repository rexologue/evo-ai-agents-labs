"""Инструмент запуска профильного агента."""

from __future__ import annotations

from fastmcp import Context
from mcp.shared.exceptions import ErrorData, McpError
from mcp.types import TextContent
from opentelemetry import trace
from pydantic import Field

from ..mcp_instance import mcp
from ..profile_agent import run_profile_agent
from .utils import ToolResult, _require_env_vars

tracer = trace.get_tracer(__name__)


@mcp.tool(
    name="generate_company_profile",
    description="""🤖 Генерирует и сохраняет профиль компании на основе текстового описания.""",
)
async def generate_company_profile(
    description: str = Field(
        ..., description="Текстовое описание компании для генерации профиля"
    ),
    ctx: Context = None,
) -> ToolResult:
    """Создает структурированный профиль компании и сохраняет его через db-mcp.

    Args:
        description: Текстовое описание компании.
        ctx: Контекст MCP для логирования и прогресса.

    Returns:
        ToolResult: Сводка по сгенерированному профилю и идентификатор сохраненной записи.

    Raises:
        McpError: В случае ошибок LLM или сохранения в БД.
    """

    _require_env_vars(["LLM_API_KEY", "DB_MCP_URL"])

    with tracer.start_as_current_span("generate_company_profile") as span:
        span.set_attribute("description.length", len(description))
        await ctx.info("🚀 Запускаем профильного агента")
        await ctx.report_progress(progress=0, total=100)

        try:
            await ctx.info("🧠 Генерируем базовый профиль")
            await ctx.report_progress(progress=25, total=100)
            result = await run_profile_agent(description)
        except Exception as exc:
            span.set_attribute("error", str(exc))
            await ctx.error(f"❌ Ошибка агента: {exc}")
            raise McpError(
                ErrorData(code=-32603, message=f"Не удалось сгенерировать профиль: {exc}")
            )

        await ctx.report_progress(progress=75, total=100)
        await ctx.info("✅ Профиль сохранен в db-mcp")

        span.set_attribute("success", True)
        span.set_attribute("company.id", result.get("company_id", ""))

        await ctx.report_progress(progress=100, total=100)

        return ToolResult(
            content=[
                TextContent(
                    type="text",
                    text=result.get(
                        "summary",
                        "Профиль компании сгенерирован и сохранен.",
                    ),
                )
            ],
            structured_content=result,
            meta={"operation": "generate_company_profile"},
        )
