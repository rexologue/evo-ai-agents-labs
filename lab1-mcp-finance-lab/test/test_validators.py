"""Тесты для модуля validators."""

import pytest
from src.validators import (
    check_principal,
    check_rate,
    check_months,
    check_initial_amount,
    check_contribution,
)


class TestValidators:
    """Тесты для валидаторов."""

    def test_check_principal_valid(self):
        """Тест валидной суммы кредита."""
        check_principal(1000000)
        check_principal(1)
        check_principal(1000000000)

    def test_check_principal_invalid(self):
        """Тест невалидной суммы кредита."""
        with pytest.raises(ValueError):
            check_principal(0)
        
        with pytest.raises(ValueError):
            check_principal(-1000)
        
        with pytest.raises(ValueError):
            check_principal(2e9)  # Превышает лимит

    def test_check_rate_valid(self):
        """Тест валидной процентной ставки."""
        check_rate(0)
        check_rate(12)
        check_rate(200)

    def test_check_rate_invalid(self):
        """Тест невалидной процентной ставки."""
        with pytest.raises(ValueError):
            check_rate(-1)
        
        with pytest.raises(ValueError):
            check_rate(201)  # Превышает лимит

    def test_check_months_valid(self):
        """Тест валидного срока."""
        check_months(1)
        check_months(12)
        check_months(600)

    def test_check_months_invalid(self):
        """Тест невалидного срока."""
        with pytest.raises(ValueError):
            check_months(0)
        
        with pytest.raises(ValueError):
            check_months(-1)
        
        with pytest.raises(ValueError):
            check_months(601)  # Превышает лимит

    def test_check_initial_amount_valid(self):
        """Тест валидной начальной суммы."""
        check_initial_amount(0)
        check_initial_amount(100000)
        check_initial_amount(1000000000)

    def test_check_initial_amount_invalid(self):
        """Тест невалидной начальной суммы."""
        with pytest.raises(ValueError):
            check_initial_amount(-1)
        
        with pytest.raises(ValueError):
            check_initial_amount(2e9)  # Превышает лимит

    def test_check_contribution_valid(self):
        """Тест валидного взноса."""
        check_contribution(0)
        check_contribution(10000)
        check_contribution(100000000)

    def test_check_contribution_invalid(self):
        """Тест невалидного взноса."""
        with pytest.raises(ValueError):
            check_contribution(-1)
        
        with pytest.raises(ValueError):
            check_contribution(2e8)  # Превышает лимит
