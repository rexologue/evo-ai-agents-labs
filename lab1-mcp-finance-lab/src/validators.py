from utils import is_finite
from config import (
    MAX_PRINCIPAL, MAX_CONTRIBUTION, MAX_MONTHS, MAX_RATE, MAX_BALANCE_CAP
)

def validate_positive_number(name: str, value: float, min_inclusive: float, max_inclusive: float) -> None:
    if not is_finite(value):
        raise ValueError(f"{name}: значение не является конечным числом.")
    if value < min_inclusive:
        raise ValueError(f"{name}: значение должно быть ≥ {min_inclusive}.")
    if value > max_inclusive:
        raise ValueError(f"{name}: значение слишком велико (>{max_inclusive}).")

def validate_int_range(name: str, value: int, min_inclusive: int, max_inclusive: int) -> None:
    if not isinstance(value, int):
        raise ValueError(f"{name}: значение должно быть целым числом.")
    if value < min_inclusive or value > max_inclusive:
        raise ValueError(f"{name}: значение должно быть в диапазоне [{min_inclusive}; {max_inclusive}].")

# Готовые профили проверок (для краткости использования в tools.py)
def check_principal(x: float) -> None:
    validate_positive_number("principal", x, 1e-9, MAX_PRINCIPAL)

def check_rate(x: float) -> None:
    validate_positive_number("annual_rate_percent", x, 0.0, MAX_RATE)

def check_months(x: int) -> None:
    validate_int_range("months", x, 1, MAX_MONTHS)

def check_initial_amount(x: float) -> None:
    validate_positive_number("initial_amount", x, 0.0, MAX_PRINCIPAL)

def check_contribution(x: float) -> None:
    validate_positive_number("monthly_contribution", x, 0.0, MAX_CONTRIBUTION)

def balance_cap() -> float:
    return MAX_BALANCE_CAP
