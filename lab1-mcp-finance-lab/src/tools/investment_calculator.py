"""Инструмент для расчета инвестиций."""

from fastmcp import Context
from mcp.types import TextContent
from opentelemetry import trace
from pydantic import Field

from mcp_instance import mcp
from ..calculations import investment_calculator as calculate_investment
from ..validators import check_initial_amount, check_rate, check_months, check_contribution
from ..metrics import TOOL_CALLS, CALCULATION_ERRORS, API_CALLS
from .utils import ToolResult, format_calculation_result

tracer = trace.get_tracer(__name__)


@mcp.tool(
    name="investment_calculator",
    description="""Калькулятор инвестиций с регулярными взносами и капитализацией.

Рассчитывает рост инвестиций с учетом регулярных взносов и сложных процентов.
Показывает помесячный график роста капитала, накопленные проценты и итоговую сумму.
"""
)
async def investment_calculator_tool(
    initial_amount: float = Field(
        ...,
        description="Начальная сумма инвестиций (≥ 0, ≤ лимита)"
    ),
    annual_rate_percent: float = Field(
        ...,
        description="Годовая доходность в процентах (0..лимит)"
    ),
    months: int = Field(
        ...,
        description="Срок инвестирования в месяцах (1..лимит)"
    ),
    monthly_contribution: float = Field(
        ...,
        description="Ежемесячный взнос (≥ 0, ≤ лимита)"
    ),
    contribution_at_beginning: bool = Field(
        ...,
        description="True — взнос в начале месяца, False — в конце"
    ),
    ctx: Context = None
) -> ToolResult:
    """
    Калькулятор инвестиций с регулярными взносами и капитализацией.

    Рассчитывает рост инвестиций с учетом регулярных взносов и сложных процентов.
    Показывает помесячный график роста капитала, накопленные проценты и итоговую сумму.

    Args:
        initial_amount: Начальная сумма инвестиций (≥ 0, ≤ лимита).
        annual_rate_percent: Годовая доходность в процентах (0..лимит).
        months: Срок инвестирования в месяцах (1..лимит).
        monthly_contribution: Ежемесячный взнос (≥ 0, ≤ лимита).
        contribution_at_beginning: True — взнос в начале месяца, False — в конце.
        ctx: Контекст для логирования и прогресс-отчетов.

    Returns:
        ToolResult: Результат расчета с графиком роста инвестиций и метриками.

    Raises:
        McpError: При неверных параметрах или ошибках расчета.
    """
    tool_name = "investment_calculator"
    
    with tracer.start_as_current_span(tool_name) as span:
        span.set_attribute("initial_amount", initial_amount)
        span.set_attribute("annual_rate_percent", annual_rate_percent)
        span.set_attribute("months", months)
        span.set_attribute("monthly_contribution", monthly_contribution)
        span.set_attribute("contribution_at_beginning", contribution_at_beginning)
        
        if ctx:
            contrib_timing = "начало" if contribution_at_beginning else "конец"
            await ctx.info(f"📈 Рассчитываем инвестиции: начальная сумма {initial_amount} руб., доходность {annual_rate_percent}% годовых, {months} мес., взносы {monthly_contribution} руб. ({contrib_timing} месяца)")
            await ctx.report_progress(progress=0, total=100)
        
        API_CALLS.labels(
            service="mcp",
            endpoint=tool_name,
            status="started"
        ).inc()
        
        try:
            # Валидация параметров
            check_initial_amount(initial_amount)
            check_rate(annual_rate_percent)
            check_months(months)
            check_contribution(monthly_contribution)
            if not isinstance(contribution_at_beginning, bool):
                from mcp.shared.exceptions import McpError, ErrorData
                raise McpError(
                    ErrorData(
                        code=-32602,  # Invalid params
                        message="contribution_at_beginning должен быть булевым (True/False)."
                    )
                )
            
            if ctx:
                await ctx.report_progress(progress=50, total=100)
            
            # Выполнение расчета
            result = calculate_investment(initial_amount, annual_rate_percent, months, monthly_contribution, contribution_at_beginning)
            
            if ctx:
                await ctx.report_progress(progress=100, total=100)
                await ctx.info("✅ Расчет завершен успешно")
            
            # Форматирование результата
            formatted_text = format_calculation_result(result, "Калькулятор инвестиций")
            
            summary = result.get("summary", {})
            growth_metrics = result.get("growth_metrics", {})
            span.set_attribute("success", True)
            span.set_attribute("final_balance", summary.get("final_balance", 0))
            span.set_attribute("roi_percent", growth_metrics.get("roi_percent", 0))
            span.set_attribute("capital_gain", growth_metrics.get("capital_gain", 0))
            
            TOOL_CALLS.labels(tool_name=tool_name, status="success").inc()
            API_CALLS.labels(
                service="mcp",
                endpoint=tool_name,
                status="success"
            ).inc()
            
            return ToolResult(
                content=[TextContent(type="text", text=formatted_text)],
                structured_content=result,
                meta={
                    "tool_name": tool_name,
                    "initial_amount": initial_amount,
                    "annual_rate_percent": annual_rate_percent,
                    "months": months,
                    "monthly_contribution": monthly_contribution,
                    "contribution_at_beginning": contribution_at_beginning,
                }
            )
            
        except ValueError as e:
            span.set_attribute("error", "validation_error")
            span.set_attribute("error_message", str(e))
            
            TOOL_CALLS.labels(tool_name=tool_name, status="validation_error").inc()
            CALCULATION_ERRORS.labels(tool_name=tool_name, error_type="validation").inc()
            API_CALLS.labels(
                service="mcp",
                endpoint=tool_name,
                status="error"
            ).inc()
            
            if ctx:
                await ctx.error(f"❌ Ошибка валидации: {e}")
            
            from mcp.shared.exceptions import McpError, ErrorData
            raise McpError(
                ErrorData(
                    code=-32602,  # Invalid params
                    message=f"Неверные параметры: {e}"
                )
            )
        except Exception as e:
            span.set_attribute("error", "calculation_error")
            span.set_attribute("error_message", str(e))
            
            TOOL_CALLS.labels(tool_name=tool_name, status="error").inc()
            CALCULATION_ERRORS.labels(tool_name=tool_name, error_type="calculation").inc()
            API_CALLS.labels(
                service="mcp",
                endpoint=tool_name,
                status="error"
            ).inc()
            
            if ctx:
                await ctx.error(f"❌ Ошибка расчета: {e}")
            
            from mcp.shared.exceptions import McpError, ErrorData
            raise McpError(
                ErrorData(
                    code=-32603,  # Internal error
                    message=f"Ошибка при выполнении расчета: {e}"
                )
            )
