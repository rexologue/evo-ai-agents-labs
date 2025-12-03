from typing import Dict, Any, List
from utils import round2
from validators import balance_cap

def annuity_schedule(principal: float, annual_rate_percent: float, months: int) -> Dict[str, Any]:
    P = float(principal)
    n = int(months)
    r = float(annual_rate_percent) / 100.0 / 12.0

    schedule: List[Dict[str, float]] = []
    remaining = P
    cum_i = 0.0
    cum_p = 0.0

    monthly_payment = P / n if r == 0.0 else P * r / (1.0 - (1.0 + r) ** (-n))

    total_paid = 0.0
    for m in range(1, n + 1):
        interest = 0.0 if r == 0.0 else remaining * r
        principal_component = monthly_payment - interest
        if m == n:
            principal_component = remaining
            monthly = principal_component + interest
        else:
            monthly = monthly_payment

        interest = round2(interest)
        principal_component = round2(principal_component)
        monthly = round2(monthly)

        remaining = round2(remaining - principal_component)
        cum_i = round2(cum_i + interest)
        cum_p = round2(cum_p + principal_component)
        total_paid = round2(total_paid + monthly)

        if remaining < -0.01:
            raise ValueError("Численная ошибка: остаток кредита стал отрицательным.")

        schedule.append({
            "month": float(m),
            "payment": monthly,
            "interest": interest,
            "principal_component": principal_component,
            "remaining_principal": max(0.0, remaining),
            "cumulative_interest": cum_i,
            "cumulative_principal": cum_p,
        })

    summary = {
        "principal": round2(P),
        "annual_rate_percent": round2(annual_rate_percent),
        "months": float(n),
        "monthly_payment": round2(monthly_payment if r != 0.0 else P / n),
        "total_paid": total_paid,
        "total_interest": cum_i,
    }
    return {"summary": summary, "schedule": schedule}


def differential_schedule(principal: float, annual_rate_percent: float, months: int) -> Dict[str, Any]:
    P = float(principal)
    n = int(months)
    r = float(annual_rate_percent) / 100.0 / 12.0

    principal_component_raw = P / n
    remaining = P
    cum_i = 0.0
    cum_p = 0.0
    schedule: List[Dict[str, float]] = []

    total_paid = 0.0
    first_payment = 0.0
    last_payment = 0.0

    for m in range(1, n + 1):
        interest = remaining * r
        principal_component = principal_component_raw if m < n else remaining
        payment = principal_component + interest

        interest = round2(interest)
        principal_component = round2(principal_component)
        payment = round2(payment)

        remaining = round2(remaining - principal_component)
        cum_i = round2(cum_i + interest)
        cum_p = round2(cum_p + principal_component)
        total_paid = round2(total_paid + payment)

        if m == 1:
            first_payment = payment
        if m == n:
            last_payment = payment

        schedule.append({
            "month": float(m),
            "payment": payment,
            "interest": interest,
            "principal_component": principal_component,
            "remaining_principal": max(0.0, remaining),
            "cumulative_interest": cum_i,
            "cumulative_principal": cum_p,
        })

        if remaining < -0.01:
            raise ValueError("Численная ошибка: остаток кредита стал отрицательным.")

    summary = {
        "principal": round2(P),
        "annual_rate_percent": round2(annual_rate_percent),
        "months": float(n),
        "first_month_payment": first_payment,
        "last_month_payment": last_payment,
        "total_paid": total_paid,
        "total_interest": cum_i,
    }
    return {"summary": summary, "schedule": schedule}


def deposit_schedule(initial_amount: float, annual_rate_percent: float, months: int,
                     monthly_contribution: float, contribution_at_beginning: bool) -> Dict[str, Any]:
    balance = float(initial_amount)
    r = float(annual_rate_percent) / 100.0 / 12.0
    n = int(months)
    contrib = float(monthly_contribution)

    schedule: List[Dict[str, float]] = []
    cum_i = 0.0
    cum_c = 0.0
    cap = balance_cap()

    for m in range(1, n + 1):
        starting = balance

        if contribution_at_beginning:
            balance = round2(balance + contrib)
            cum_c = round2(cum_c + contrib)

        interest = round2(balance * r)
        balance = round2(balance + interest)
        cum_i = round2(cum_i + interest)

        if not contribution_at_beginning:
            balance = round2(balance + contrib)
            cum_c = round2(cum_c + contrib)

        if balance > cap:
            raise ValueError(
                "Итоговый баланс превысил верхнюю границу (проверьте ставку/срок/взносы)."
            )

        schedule.append({
            "month": float(m),
            "starting_balance": round2(starting),
            "contribution": round2(contrib),
            "interest_earned": interest,
            "ending_balance": round2(balance),
            "cumulative_contributions": cum_c,
            "cumulative_interest": cum_i,
        })

    summary = {
        "initial_amount": round2(float(initial_amount)),
        "annual_rate_percent": round2(annual_rate_percent),
        "months": float(n),
        "monthly_contribution": round2(contrib),
        "contribution_at_beginning": 1.0 if contribution_at_beginning else 0.0,
        "final_balance": round2(balance),
        "total_contributions": cum_c,
        "total_interest": cum_i,
    }
    return {"summary": summary, "schedule": schedule}


def compare_loans(principal: float, annual_rate_percent: float, months: int) -> Dict[str, Any]:
    """
    Сравнение аннуитетного и дифференцированного кредитов.
    
    Рассчитывает оба типа кредитов и сравнивает их по:
    - Общей сумме выплат
    - Переплате по процентам
    - Разнице в платежах
    - Преимуществам каждого типа
    
    Args:
        principal: Сумма кредита
        annual_rate_percent: Годовая ставка в процентах
        months: Срок в месяцах
        
    Returns:
        Словарь с результатами сравнения
    """
    # Рассчитываем оба типа кредитов
    annuity_result = annuity_schedule(principal, annual_rate_percent, months)
    differential_result = differential_schedule(principal, annual_rate_percent, months)
    
    annuity_summary = annuity_result["summary"]
    differential_summary = differential_result["summary"]
    
    # Извлекаем ключевые показатели
    annuity_total_paid = annuity_summary["total_paid"]
    differential_total_paid = differential_summary["total_paid"]
    annuity_interest = annuity_summary["total_interest"]
    differential_interest = differential_summary["total_interest"]
    
    # Вычисляем разницу
    total_paid_diff = round2(annuity_total_paid - differential_total_paid)
    interest_diff = round2(annuity_interest - differential_interest)
    
    # Определяем, какой кредит выгоднее
    if total_paid_diff > 0:
        cheaper_type = "дифференцированный"
        savings = total_paid_diff
        recommendation = (
            "Дифференцированный кредит выгоднее по общей сумме выплат. "
            "Однако учтите, что первые платежи будут выше, чем при аннуитетной схеме."
        )
    elif total_paid_diff < 0:
        cheaper_type = "аннуитетный"
        savings = abs(total_paid_diff)
        recommendation = (
            "Аннуитетный кредит выгоднее по общей сумме выплат. "
            "Платежи будут одинаковыми каждый месяц, что удобно для планирования бюджета."
        )
    else:
        cheaper_type = "равны"
        savings = 0.0
        recommendation = "Оба типа кредитов имеют одинаковую общую сумму выплат."
    
    # Преимущества каждого типа
    annuity_advantages = [
        "Фиксированный ежемесячный платеж - удобно планировать бюджет",
        "Меньше нагрузка в первые месяцы по сравнению с дифференцированным",
        "Проще управлять личными финансами"
    ]
    
    differential_advantages = [
        "Меньшая общая переплата по процентам",
        "Быстрее уменьшается основной долг",
        "Меньше общая сумма выплат"
    ]
    
    comparison = {
        "principal": round2(principal),
        "annual_rate_percent": round2(annual_rate_percent),
        "months": float(months),
        "annuity": {
            "total_paid": annuity_total_paid,
            "total_interest": annuity_interest,
            "monthly_payment": annuity_summary["monthly_payment"],
            "overpayment_percent": round2((annuity_interest / principal) * 100),
        },
        "differential": {
            "total_paid": differential_total_paid,
            "total_interest": differential_interest,
            "first_month_payment": differential_summary["first_month_payment"],
            "last_month_payment": differential_summary["last_month_payment"],
            "overpayment_percent": round2((differential_interest / principal) * 100),
        },
        "difference": {
            "total_paid_diff": total_paid_diff,
            "interest_diff": interest_diff,
            "cheaper_type": cheaper_type,
            "savings": savings,
        },
        "annuity_advantages": annuity_advantages,
        "differential_advantages": differential_advantages,
        "recommendation": recommendation,
    }
    
    return {
        "comparison": comparison,
        "annuity": annuity_result,
        "differential": differential_result,
    }


def investment_calculator(
    initial_amount: float,
    annual_rate_percent: float,
    months: int,
    monthly_contribution: float,
    contribution_at_beginning: bool
) -> Dict[str, Any]:
    """
    Калькулятор инвестиций с регулярными взносами и капитализацией.
    
    Рассчитывает рост инвестиций с учетом регулярных взносов и сложных процентов.
    Показывает помесячный график роста капитала, накопленные проценты и итоговую сумму.
    
    Args:
        initial_amount: Начальная сумма инвестиций
        annual_rate_percent: Годовая доходность в процентах
        months: Срок инвестирования в месяцах
        monthly_contribution: Ежемесячный взнос
        contribution_at_beginning: True - взнос в начале месяца, False - в конце
        
    Returns:
        Словарь с результатами расчета инвестиций
    """
    # Используем существующую функцию deposit_schedule для расчета
    deposit_result = deposit_schedule(
        initial_amount,
        annual_rate_percent,
        months,
        monthly_contribution,
        contribution_at_beginning
    )
    
    summary = deposit_result["summary"]
    schedule = deposit_result["schedule"]
    
    # Вычисляем дополнительные метрики для инвестиций
    final_balance = summary["final_balance"]
    total_contributions = summary["total_contributions"]
    total_interest = summary["total_interest"]
    initial_investment = summary["initial_amount"]
    
    # ROI (Return on Investment) в процентах
    total_invested = initial_investment + total_contributions
    roi_percent = round2(((final_balance - total_invested) / total_invested) * 100) if total_invested > 0 else 0.0
    
    # Средняя годовая доходность
    years = months / 12.0
    if years > 0:
        # Формула: (итоговая_сумма / начальная_сумма) ^ (1/лет) - 1
        if initial_investment > 0:
            annualized_return = round2((((final_balance / total_invested) ** (1.0 / years)) - 1.0) * 100)
        else:
            annualized_return = 0.0
    else:
        annualized_return = 0.0
    
    # Прирост капитала
    capital_gain = round2(final_balance - total_invested)
    
    # Процент от общей суммы, который составляет прибыль
    profit_percent = round2((total_interest / final_balance) * 100) if final_balance > 0 else 0.0
    
    growth_metrics = {
        "roi_percent": roi_percent,
        "annualized_return_percent": annualized_return,
        "capital_gain": capital_gain,
        "profit_percent": profit_percent,
        "total_invested": total_invested,
        "final_value": final_balance,
        "years": round2(years),
    }
    
    # Формируем итоговый summary с инвестиционными метриками
    investment_summary = {
        **summary,
        "roi_percent": roi_percent,
        "annualized_return_percent": annualized_return,
        "capital_gain": capital_gain,
        "total_invested": total_invested,
    }
    
    return {
        "summary": investment_summary,
        "schedule": schedule,
        "growth_metrics": growth_metrics,
    }
