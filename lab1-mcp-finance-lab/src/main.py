import os

from fastmcp import FastMCP
from typing import Dict, Any
from validators import (
    check_principal, check_rate, check_months,
    check_initial_amount, check_contribution
)
from calculations import (
    annuity_schedule, differential_schedule, deposit_schedule
)

# Единый экземпляр FastMCP, к которому подключаются все тулы.
mcp = FastMCP("Finance Schedules")


@mcp.tool
def loan_schedule_annuity(principal: float, annual_rate_percent: float, months: int) -> Dict[str, Any]:
    """
    Аннуитетный кредит: расчёт фиксированного ежемесячного платежа и помесячного графика.

    Инструмент строит таблицу платежей по аннуитетной схеме. Для каждого месяца возвращаются:
    - payment: платёж, interest: проценты, principal_component: тело, remaining_principal: остаток,
      cumulative_interest / cumulative_principal: накопленные суммы.

    Args:
        principal (float): Сумма кредита (> 0, ≤ лимита).
        annual_rate_percent (float): Годовая ставка в процентах (0..лимит).
        months (int): Срок в месяцах (1..лимит).

    Returns:
        Dict[str, Any]:
            - summary: principal, annual_rate_percent, months, monthly_payment, total_paid, total_interest
            - schedule: список записей по месяцам (см. описание выше)

    Raises:
        ValueError: При неверных/слишком больших значениях.
    Note:
        Денежные величины округляются до 2 знаков. В последний месяц — коррекция, чтобы остаток стал 0.00.
    """
    check_principal(principal)
    check_rate(annual_rate_percent)
    check_months(months)
    return annuity_schedule(principal, annual_rate_percent, months)


@mcp.tool
def loan_schedule_differential(principal: float, annual_rate_percent: float, months: int) -> Dict[str, Any]:
    """
    Дифференцированный кредит: постоянная часть тела и уменьшающиеся проценты.

    На выходе — помесячная таблица с полями:
    month, payment, interest, principal_component, remaining_principal,
    cumulative_interest, cumulative_principal.

    Args:
        principal (float): Сумма кредита (> 0, ≤ лимита).
        annual_rate_percent (float): Годовая ставка в процентах (0..лимит).
        months (int): Срок в месяцах (1..лимит).

    Returns:
        Dict[str, Any]:
            - summary: principal, annual_rate_percent, months,
              first_month_payment, last_month_payment, total_paid, total_interest
            - schedule: список строк по месяцам

    Raises:
        ValueError: При неверных/слишком больших значениях.
    Note:
        Все суммы округлены до 2 знаков. Последняя строка корректируется по копейкам.
    """
    check_principal(principal)
    check_rate(annual_rate_percent)
    check_months(months)
    return differential_schedule(principal, annual_rate_percent, months)


@mcp.tool
def deposit_schedule_compound(
    initial_amount: float,
    annual_rate_percent: float,
    months: int,
    monthly_contribution: float,
    contribution_at_beginning: bool
) -> Dict[str, Any]:
    """
    Вклад с ежемесячной капитализацией и взносами.

    Строит график: starting_balance, contribution, interest_earned, ending_balance,
    cumulative_contributions, cumulative_interest — для каждого месяца.

    Args:
        initial_amount (float): Начальная сумма (≥ 0, ≤ лимита).
        annual_rate_percent (float): Годовая ставка в процентах (0..лимит).
        months (int): Срок в месяцах (1..лимит).
        monthly_contribution (float): Ежемесячный взнос (≥ 0, ≤ лимита).
        contribution_at_beginning (bool): True — взнос в начале месяца, False — в конце.

    Returns:
        Dict[str, Any]:
            - summary: initial_amount, annual_rate_percent, months, monthly_contribution,
              contribution_at_beginning (1.0/0.0), final_balance, total_contributions, total_interest
            - schedule: помесячные строки (см. выше)

    Raises:
        ValueError: При неверных значениях или чрезмерном росте баланса.
    Note:
        Округление до 2 знаков. Есть защитная отсечка по максимальному балансу.
    """
    check_initial_amount(initial_amount)
    check_rate(annual_rate_percent)
    check_months(months)
    check_contribution(monthly_contribution)
    if not isinstance(contribution_at_beginning, bool):
        raise ValueError("contribution_at_beginning должен быть булевым (True/False).")
    return deposit_schedule(initial_amount, annual_rate_percent, months, monthly_contribution, contribution_at_beginning)


if __name__ == "__main__":
    # SSE-транспорт по умолчанию (как в вашем примере)
    # Переменной PORT можно указать другой порт, по умолчанию 8010
    mcp.run(transport="sse", host="0.0.0.0", port=os.getenv('PORT', 8000))

