"""Утилиты для MCP инструментов финансовых расчетов."""

from typing import Dict, Any, Sequence
from dataclasses import dataclass

from mcp.types import TextContent

# Попытка импортировать ToolResult из fastmcp, если не доступен - создаем обёртку
try:
    from fastmcp import ToolResult
except ImportError:
    # Создаем обёртку ToolResult если его нет в fastmcp
    @dataclass
    class ToolResult:
        """Обёртка для ToolResult если он не доступен в fastmcp."""
        content: Sequence[TextContent]
        structured_content: Dict[str, Any] | None = None
        meta: Dict[str, Any] | None = None


def format_calculation_result(result: Dict[str, Any], tool_name: str) -> str:
    """
    Форматирует результат финансового расчета в человеко-читаемый текст.
    
    Args:
        result: Результат расчета из calculations.py
        tool_name: Имя инструмента для контекста
        
    Returns:
        Отформатированная строка с результатами
    """
    summary = result.get("summary", {})
    schedule = result.get("schedule", [])
    growth_metrics = result.get("growth_metrics", {})
    
    formatted = f"## Результаты расчета ({tool_name})\n\n"
    
    # Добавляем сводку
    if "monthly_payment" in summary:
        formatted += f"**Ежемесячный платеж:** {summary['monthly_payment']:.2f} руб.\n"
    if "first_month_payment" in summary:
        formatted += f"**Первый платеж:** {summary['first_month_payment']:.2f} руб.\n"
        formatted += f"**Последний платеж:** {summary['last_month_payment']:.2f} руб.\n"
    if "total_paid" in summary:
        formatted += f"**Общая сумма выплат:** {summary['total_paid']:.2f} руб.\n"
    if "total_interest" in summary:
        formatted += f"**Переплата по процентам:** {summary['total_interest']:.2f} руб.\n"
    if "final_balance" in summary:
        formatted += f"**Итоговый баланс:** {summary['final_balance']:.2f} руб.\n"
    if "total_contributions" in summary:
        formatted += f"**Общие взносы:** {summary['total_contributions']:.2f} руб.\n"
    if "total_invested" in summary:
        formatted += f"**Общие инвестиции:** {summary['total_invested']:.2f} руб.\n"
    if "roi_percent" in summary:
        formatted += f"**ROI:** {summary['roi_percent']:.2f}%\n"
    if "annualized_return_percent" in summary:
        formatted += f"**Средняя годовая доходность:** {summary['annualized_return_percent']:.2f}%\n"
    if "capital_gain" in summary:
        formatted += f"**Прирост капитала:** {summary['capital_gain']:.2f} руб.\n"
    
    formatted += "\n"
    
    # Добавляем метрики роста для инвестиций
    if growth_metrics:
        formatted += "### Метрики роста инвестиций\n"
        if "roi_percent" in growth_metrics:
            formatted += f"- **ROI:** {growth_metrics['roi_percent']:.2f}%\n"
        if "annualized_return_percent" in growth_metrics:
            formatted += f"- **Средняя годовая доходность:** {growth_metrics['annualized_return_percent']:.2f}%\n"
        if "capital_gain" in growth_metrics:
            formatted += f"- **Прирост капитала:** {growth_metrics['capital_gain']:.2f} руб.\n"
        if "years" in growth_metrics:
            formatted += f"- **Срок инвестирования:** {growth_metrics['years']:.2f} лет\n"
        formatted += "\n"
    
    # Добавляем краткую информацию о графике
    if schedule:
        formatted += f"**График:** {len(schedule)} месяцев\n"
        if len(schedule) <= 12:
            formatted += "\n### Помесячный график:\n\n"
            for entry in schedule:
                month = int(entry.get("month", 0))
                if "payment" in entry:
                    formatted += f"Месяц {month}: Платеж {entry['payment']:.2f} руб. "
                    formatted += f"(Проценты: {entry['interest']:.2f} руб., Тело: {entry['principal_component']:.2f} руб.)\n"
                elif "ending_balance" in entry:
                    formatted += f"Месяц {month}: Баланс {entry['ending_balance']:.2f} руб. "
                    formatted += f"(Взнос: {entry.get('contribution', 0):.2f} руб., Проценты: {entry.get('interest_earned', 0):.2f} руб.)\n"
        else:
            formatted += f"\nПервые 3 месяца:\n"
            for entry in schedule[:3]:
                month = int(entry.get("month", 0))
                if "payment" in entry:
                    formatted += f"Месяц {month}: {entry['payment']:.2f} руб.\n"
                elif "ending_balance" in entry:
                    formatted += f"Месяц {month}: {entry['ending_balance']:.2f} руб.\n"
            formatted += f"... и еще {len(schedule) - 3} месяцев\n"
    
    return formatted
