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
