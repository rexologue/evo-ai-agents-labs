package validators

import (
	"fmt"

	"github.com/cloud-ru/mcp-finance-go/internal/config"
	"github.com/cloud-ru/mcp-finance-go/pkg/utils"
)

// ValidatePositiveNumber проверяет, что число положительное и в допустимом диапазоне
func ValidatePositiveNumber(name string, value float64, minInclusive, maxInclusive float64) error {
	if !utils.IsFinite(value) {
		return fmt.Errorf("%s: значение не является конечным числом", name)
	}
	if value < minInclusive {
		return fmt.Errorf("%s: значение должно быть ≥ %.0f", name, minInclusive)
	}
	if value > maxInclusive {
		return fmt.Errorf("%s: значение слишком велико (>%.0f)", name, maxInclusive)
	}
	return nil
}

// ValidateIntRange проверяет, что целое число в допустимом диапазоне
func ValidateIntRange(name string, value int, minInclusive, maxInclusive int) error {
	if value < minInclusive || value > maxInclusive {
		return fmt.Errorf("%s: значение должно быть в диапазоне [%d; %d]", name, minInclusive, maxInclusive)
	}
	return nil
}

// CheckPrincipal проверяет сумму кредита
func CheckPrincipal(cfg *config.Config, principal float64) error {
	return ValidatePositiveNumber("principal", principal, 1e-9, cfg.MaxPrincipal)
}

// CheckRate проверяет процентную ставку
func CheckRate(cfg *config.Config, rate float64) error {
	return ValidatePositiveNumber("annual_rate_percent", rate, 0.0, cfg.MaxRate)
}

// CheckMonths проверяет срок в месяцах
func CheckMonths(cfg *config.Config, months int) error {
	return ValidateIntRange("months", months, 1, cfg.MaxMonths)
}

// CheckInitialAmount проверяет начальную сумму
func CheckInitialAmount(cfg *config.Config, amount float64) error {
	return ValidatePositiveNumber("initial_amount", amount, 0.0, cfg.MaxPrincipal)
}

// CheckContribution проверяет ежемесячный взнос
func CheckContribution(cfg *config.Config, contribution float64) error {
	return ValidatePositiveNumber("monthly_contribution", contribution, 0.0, cfg.MaxContribution)
}

// BalanceCap возвращает максимальный баланс
func BalanceCap(cfg *config.Config) float64 {
	if cfg == nil {
		return 1e12 // Значение по умолчанию
	}
	return cfg.BalanceCap()
}
