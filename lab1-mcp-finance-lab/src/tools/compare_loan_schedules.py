"""Инструмент для сравнения типов кредитов."""

from fastmcp import Context
from mcp.types import TextContent
from opentelemetry import trace
from pydantic import Field

from mcp_instance import mcp
from ..calculations import compare_loans
from ..validators import check_principal, check_rate, check_months
from ..metrics import TOOL_CALLS, CALCULATION_ERRORS, API_CALLS
from .utils import ToolResult

tracer = trace.get_tracer(__name__)


def format_comparison_result(result: dict) -> str:
    """Форматирует результат сравнения кредитов."""
    comparison = result.get("comparison", {})
    annuity = comparison.get("annuity", {})
    differential = comparison.get("differential", {})
    diff = comparison.get("difference", {})
    
    formatted = "## Сравнение типов кредитов\n\n"
    
    formatted += f"**Параметры кредита:**\n"
    formatted += f"- Сумма: {comparison.get('principal', 0):.2f} руб.\n"
    formatted += f"- Ставка: {comparison.get('annual_rate_percent', 0):.2f}% годовых\n"
    formatted += f"- Срок: {int(comparison.get('months', 0))} месяцев\n\n"
    
    formatted += "### Аннуитетный кредит\n"
    formatted += f"- Ежемесячный платеж: {annuity.get('monthly_payment', 0):.2f} руб.\n"
    formatted += f"- Общая сумма выплат: {annuity.get('total_paid', 0):.2f} руб.\n"
    formatted += f"- Переплата: {annuity.get('total_interest', 0):.2f} руб. ({annuity.get('overpayment_percent', 0):.2f}%)\n\n"
    
    formatted += "### Дифференцированный кредит\n"
    formatted += f"- Первый платеж: {differential.get('first_month_payment', 0):.2f} руб.\n"
    formatted += f"- Последний платеж: {differential.get('last_month_payment', 0):.2f} руб.\n"
    formatted += f"- Общая сумма выплат: {differential.get('total_paid', 0):.2f} руб.\n"
    formatted += f"- Переплата: {differential.get('total_interest', 0):.2f} руб. ({differential.get('overpayment_percent', 0):.2f}%)\n\n"
    
    formatted += "### Сравнение\n"
    formatted += f"- Разница в общей сумме: {diff.get('total_paid_diff', 0):.2f} руб.\n"
    formatted += f"- Разница в переплате: {diff.get('interest_diff', 0):.2f} руб.\n"
    formatted += f"- Более выгодный тип: {diff.get('cheaper_type', 'не определен')}\n"
    if diff.get('savings', 0) > 0:
        formatted += f"- Экономия: {diff.get('savings', 0):.2f} руб.\n"
    formatted += "\n"
    
    formatted += "### Преимущества аннуитетного кредита\n"
    advantages = comparison.get("annuity_advantages", [])
    for adv in advantages:
        formatted += f"- {adv}\n"
    formatted += "\n"
    
    formatted += "### Преимущества дифференцированного кредита\n"
    advantages = comparison.get("differential_advantages", [])
    for adv in advantages:
        formatted += f"- {adv}\n"
    formatted += "\n"
    
    formatted += f"### Рекомендация\n{comparison.get('recommendation', '')}\n"
    
    return formatted


@mcp.tool(
    name="compare_loan_schedules",
    description="""Сравнение аннуитетного и дифференцированного кредитов.

Инструмент сравнивает два типа кредитов с одинаковыми параметрами и показывает:
- Общую сумму выплат для каждого типа
- Переплату по процентам
- Разницу в платежах
- Преимущества каждого типа кредита
"""
)
async def compare_loan_schedules(
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
    Сравнение аннуитетного и дифференцированного кредитов.

    Инструмент сравнивает два типа кредитов с одинаковыми параметрами и показывает:
    - Общую сумму выплат для каждого типа
    - Переплату по процентам
    - Разницу в платежах
    - Преимущества каждого типа кредита

    Args:
        principal: Сумма кредита (> 0, ≤ лимита).
        annual_rate_percent: Годовая ставка в процентах (0..лимит).
        months: Срок в месяцах (1..лимит).
        ctx: Контекст для логирования и прогресс-отчетов.

    Returns:
        ToolResult: Результат сравнения с рекомендацией.

    Raises:
        McpError: При неверных параметрах или ошибках расчета.
    """
    tool_name = "compare_loan_schedules"
    
    with tracer.start_as_current_span(tool_name) as span:
        span.set_attribute("principal", principal)
        span.set_attribute("annual_rate_percent", annual_rate_percent)
        span.set_attribute("months", months)
        
        if ctx:
            await ctx.info(f"⚖️ Сравниваем типы кредитов: {principal} руб., {annual_rate_percent}% годовых, {months} мес.")
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
            
            # Выполнение сравнения
            result = compare_loans(principal, annual_rate_percent, months)
            
            if ctx:
                await ctx.report_progress(progress=100, total=100)
                await ctx.info("✅ Сравнение завершено успешно")
            
            # Форматирование результата
            formatted_text = format_comparison_result(result)
            
            comparison = result.get("comparison", {})
            span.set_attribute("success", True)
            span.set_attribute("cheaper_type", comparison.get("difference", {}).get("cheaper_type", "unknown"))
            span.set_attribute("savings", comparison.get("difference", {}).get("savings", 0))
            
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
