"""Тесты для модуля calculations."""

import pytest
from src.calculations import (
    annuity_schedule,
    differential_schedule,
    deposit_schedule,
    compare_loans,
    investment_calculator,
)


class TestAnnuitySchedule:
    """Тесты для аннуитетного кредита."""

    def test_basic_annuity(self):
        """Базовый тест аннуитетного кредита."""
        result = annuity_schedule(principal=1000000, annual_rate_percent=12, months=12)
        
        assert "summary" in result
        assert "schedule" in result
        assert len(result["schedule"]) == 12
        
        summary = result["summary"]
        assert summary["principal"] == 1000000.0
        assert summary["annual_rate_percent"] == 12.0
        assert summary["months"] == 12.0
        assert summary["monthly_payment"] > 0
        assert summary["total_paid"] > summary["principal"]
        assert summary["total_interest"] > 0
        
        # Проверяем, что остаток в последнем месяце равен 0
        last_month = result["schedule"][-1]
        assert last_month["remaining_principal"] == 0.0

    def test_zero_rate(self):
        """Тест с нулевой процентной ставкой."""
        result = annuity_schedule(principal=100000, annual_rate_percent=0, months=10)
        
        summary = result["summary"]
        assert summary["monthly_payment"] == 10000.0
        assert summary["total_interest"] == 0.0
        assert summary["total_paid"] == summary["principal"]


class TestDifferentialSchedule:
    """Тесты для дифференцированного кредита."""

    def test_basic_differential(self):
        """Базовый тест дифференцированного кредита."""
        result = differential_schedule(principal=1000000, annual_rate_percent=12, months=12)
        
        assert "summary" in result
        assert "schedule" in result
        assert len(result["schedule"]) == 12
        
        summary = result["summary"]
        assert summary["principal"] == 1000000.0
        assert summary["first_month_payment"] > summary["last_month_payment"]
        assert summary["total_paid"] > summary["principal"]
        assert summary["total_interest"] > 0
        
        # Проверяем, что остаток в последнем месяце равен 0
        last_month = result["schedule"][-1]
        assert last_month["remaining_principal"] == 0.0


class TestDepositSchedule:
    """Тесты для вклада с капитализацией."""

    def test_basic_deposit(self):
        """Базовый тест вклада."""
        result = deposit_schedule(
            initial_amount=100000,
            annual_rate_percent=8,
            months=12,
            monthly_contribution=10000,
            contribution_at_beginning=True
        )
        
        assert "summary" in result
        assert "schedule" in result
        assert len(result["schedule"]) == 12
        
        summary = result["summary"]
        assert summary["initial_amount"] == 100000.0
        assert summary["final_balance"] > summary["initial_amount"]
        assert summary["total_contributions"] == 120000.0  # 12 * 10000
        assert summary["total_interest"] > 0

    def test_deposit_without_contributions(self):
        """Тест вклада без взносов."""
        result = deposit_schedule(
            initial_amount=100000,
            annual_rate_percent=8,
            months=12,
            monthly_contribution=0,
            contribution_at_beginning=False
        )
        
        summary = result["summary"]
        assert summary["total_contributions"] == 0.0
        assert summary["final_balance"] > summary["initial_amount"]


class TestCompareLoans:
    """Тесты для сравнения кредитов."""

    def test_basic_comparison(self):
        """Базовый тест сравнения кредитов."""
        result = compare_loans(principal=1000000, annual_rate_percent=12, months=12)
        
        assert "comparison" in result
        assert "annuity" in result["comparison"]
        assert "differential" in result["comparison"]
        assert "difference" in result["comparison"]
        assert "recommendation" in result
        
        comparison = result["comparison"]
        assert comparison["annuity"]["total_paid"] > 0
        assert comparison["differential"]["total_paid"] > 0
        
        # Аннуитетный кредит обычно имеет большую общую сумму выплат
        # но меньший первый платеж
        diff = comparison["difference"]
        assert "total_paid_diff" in diff
        assert "cheaper_type" in diff


class TestInvestmentCalculator:
    """Тесты для калькулятора инвестиций."""

    def test_basic_investment(self):
        """Базовый тест инвестиций."""
        result = investment_calculator(
            initial_amount=100000,
            annual_rate_percent=10,
            months=12,
            monthly_contribution=10000,
            contribution_at_beginning=True
        )
        
        assert "summary" in result
        assert "schedule" in result
        assert "growth_metrics" in result
        assert len(result["schedule"]) == 12
        
        summary = result["summary"]
        assert summary["total_invested"] > 0
        assert summary["final_balance"] > summary["total_invested"]
        
        growth_metrics = result["growth_metrics"]
        assert "roi_percent" in growth_metrics
        assert "annualized_return_percent" in growth_metrics
        assert "capital_gain" in growth_metrics

    def test_investment_without_contributions(self):
        """Тест инвестиций без взносов."""
        result = investment_calculator(
            initial_amount=100000,
            annual_rate_percent=10,
            months=12,
            monthly_contribution=0,
            contribution_at_beginning=False
        )
        
        summary = result["summary"]
        assert summary["total_invested"] == 100000.0
        assert summary["final_balance"] > summary["total_invested"]
