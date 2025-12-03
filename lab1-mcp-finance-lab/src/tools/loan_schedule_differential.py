"""Инструмент для расчета дифференцированного кредита."""

from fastmcp import Context
from mcp.types import TextContent
from opentelemetry import trace
from pydantic import Field

from mcp_instance import mcp
from ..calculations import differential_schedule
from ..validators import check_principal, check_rate, check_months
from ..metrics import TOOL_CALLS, CALCULATION_ERRORS, API_CALLS
from .utils import ToolResult, format_calculation_result

tracer = trace.get_tracer(__name__)


@mcp.tool(
    name="loan_schedule_differential",
    description="""Дифференцированный кредит: постоянная часть тела и уменьшающиеся проценты.

На выходе — помесячная таблица с полями:
month, payment, interest, principal_component, remaining_principal,
cumulative_interest, cumulative_principal.
"""
)
async def loan_schedule_differential(
    principal: float = Field(
        ...,
        description="Сумма кредита (> 0, ≤ лимита)"
    ),
    annual_rate_percent: float = Field(
        ...,
        description="Годовая ставка в процентах (0..лимит)"
    ),
    months: int = Field(
        ...,
        description="Срок в месяцах (1..лимит)"
    ),
    ctx: Context = None
) -> ToolResult:
    """
    Дифференцированный кредит: постоянная часть тела и уменьшающиеся проценты.

    На выходе — помесячная таблица с полями:
    month, payment, interest, principal_component, remaining_principal,
    cumulative_interest, cumulative_principal.

    Args:
        principal: Сумма кредита (> 0, ≤ лимита).
        annual_rate_percent: Годовая ставка в процентах (0..лимит).
        months: Срок в месяцах (1..лимит).
        ctx: Контекст для логирования и прогресс-отчетов.

    Returns:
        ToolResult: Результат расчета с графиком платежей и сводкой.

    Raises:
        McpError: При неверных/слишком больших значениях.
    Note:
        Все суммы округлены до 2 знаков. Последняя строка корректируется по копейкам.
    """
    tool_name = "loan_schedule_differential"
    
    with tracer.start_as_current_span(tool_name) as span:
        span.set_attribute("principal", principal)
        span.set_attribute("annual_rate_percent", annual_rate_percent)
        span.set_attribute("months", months)
        
        if ctx:
            await ctx.info(f"🔢 Рассчитываем дифференцированный кредит: {principal} руб., {annual_rate_percent}% годовых, {months} мес.")
            await ctx.report_progress(progress=0, total=100)
        
        API_CALLS.labels(
            service="mcp",
            endpoint=tool_name,
            status="started"
        ).inc()
        
        try:
            # Валидация параметров
            check_principal(principal)
            check_rate(annual_rate_percent)
            check_months(months)
            
            if ctx:
                await ctx.report_progress(progress=50, total=100)
            
            # Выполнение расчета
            result = differential_schedule(principal, annual_rate_percent, months)
            
            if ctx:
                await ctx.report_progress(progress=100, total=100)
                await ctx.info("✅ Расчет завершен успешно")
            
            # Форматирование результата
            formatted_text = format_calculation_result(result, "Дифференцированный кредит")
            
            span.set_attribute("success", True)
            span.set_attribute("first_month_payment", result["summary"].get("first_month_payment", 0))
            span.set_attribute("last_month_payment", result["summary"].get("last_month_payment", 0))
            span.set_attribute("total_paid", result["summary"].get("total_paid", 0))
            
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
                    "principal": principal,
                    "annual_rate_percent": annual_rate_percent,
                    "months": months,
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
