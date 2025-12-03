package calculations

import (
	"github.com/cloud-ru/mcp-finance-go/pkg/utils"
)

// CompareLoans сравнивает аннуитетный и дифференцированный кредиты
func CompareLoans(principal, annualRatePercent float64, months int) (*ComparisonResult, error) {
	// Рассчитываем оба типа кредитов
	annuityResult, err := AnnuitySchedule(principal, annualRatePercent, months)
	if err != nil {
		return nil, err
	}

	differentialResult, err := DifferentialSchedule(principal, annualRatePercent, months)
	if err != nil {
		return nil, err
	}

	annuitySummary := annuityResult.Summary.(LoanSummary)
	differentialSummary := differentialResult.Summary.(LoanSummary)

	// Извлекаем ключевые показатели
	annuityTotalPaid := annuitySummary.TotalPaid
	differentialTotalPaid := differentialSummary.TotalPaid
	annuityInterest := annuitySummary.TotalInterest
	differentialInterest := differentialSummary.TotalInterest

	// Вычисляем разницу
	totalPaidDiff := utils.Round2(annuityTotalPaid - differentialTotalPaid)
	interestDiff := utils.Round2(annuityInterest - differentialInterest)

	// Определяем, какой кредит выгоднее
	var cheaperType string
	var savings float64
	var recommendation string

	if totalPaidDiff > 0 {
		cheaperType = "дифференцированный"
		savings = totalPaidDiff
		recommendation = "Дифференцированный кредит выгоднее по общей сумме выплат. Однако учтите, что первые платежи будут выше, чем при аннуитетной схеме."
	} else if totalPaidDiff < 0 {
		cheaperType = "аннуитетный"
		savings = -totalPaidDiff
		recommendation = "Аннуитетный кредит выгоднее по общей сумме выплат. Платежи будут одинаковыми каждый месяц, что удобно для планирования бюджета."
	} else {
		cheaperType = "равны"
		savings = 0.0
		recommendation = "Оба типа кредитов имеют одинаковую общую сумму выплат."
	}

	// Преимущества каждого типа
	annuityAdvantages := []string{
		"Фиксированный ежемесячный платеж - удобно планировать бюджет",
		"Меньше нагрузка в первые месяцы по сравнению с дифференцированным",
		"Проще управлять личными финансами",
	}

	differentialAdvantages := []string{
		"Меньшая общая переплата по процентам",
		"Быстрее уменьшается основной долг",
		"Меньше общая сумма выплат",
	}

	comparison := map[string]interface{}{
		"principal":           utils.Round2(principal),
		"annual_rate_percent": utils.Round2(annualRatePercent),
		"months":              float64(months),
		"annuity": map[string]interface{}{
			"total_paid":          annuityTotalPaid,
			"total_interest":      annuityInterest,
			"monthly_payment":     annuitySummary.MonthlyPayment,
			"overpayment_percent": utils.Round2((annuityInterest / principal) * 100),
		},
		"differential": map[string]interface{}{
			"total_paid":          differentialTotalPaid,
			"total_interest":      differentialInterest,
			"first_month_payment": differentialSummary.FirstMonthPayment,
			"last_month_payment":  differentialSummary.LastMonthPayment,
			"overpayment_percent": utils.Round2((differentialInterest / principal) * 100),
		},
		"difference": map[string]interface{}{
			"total_paid_diff": totalPaidDiff,
			"interest_diff":   interestDiff,
			"cheaper_type":    cheaperType,
			"savings":         savings,
		},
		"annuity_advantages":      annuityAdvantages,
		"differential_advantages": differentialAdvantages,
		"recommendation":          recommendation,
	}

	return &ComparisonResult{
		Comparison:   comparison,
		Annuity:      *annuityResult,
		Differential: *differentialResult,
	}, nil
}
