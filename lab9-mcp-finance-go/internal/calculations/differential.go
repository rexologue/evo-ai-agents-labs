package calculations

import (
	"fmt"

	"github.com/cloud-ru/mcp-finance-go/pkg/utils"
)

// DifferentialSchedule рассчитывает график дифференцированного кредита
func DifferentialSchedule(principal, annualRatePercent float64, months int) (*CalculationResult, error) {
	P := principal
	n := months
	r := annualRatePercent / 100.0 / 12.0

	principalComponentRaw := P / float64(n)
	remaining := P
	cumI := 0.0
	cumP := 0.0
	schedule := make([]ScheduleEntry, 0, n)

	totalPaid := 0.0
	var firstPayment, lastPayment float64

	for m := 1; m <= n; m++ {
		interest := remaining * r
		var principalComponent float64
		if m < n {
			principalComponent = principalComponentRaw
		} else {
			principalComponent = remaining
		}
		payment := principalComponent + interest

		interest = utils.Round2(interest)
		principalComponent = utils.Round2(principalComponent)
		payment = utils.Round2(payment)

		remaining = utils.Round2(remaining - principalComponent)
		cumI = utils.Round2(cumI + interest)
		cumP = utils.Round2(cumP + principalComponent)
		totalPaid = utils.Round2(totalPaid + payment)

		if m == 1 {
			firstPayment = payment
		}
		if m == n {
			lastPayment = payment
		}

		if remaining < -0.01 {
			return nil, fmt.Errorf("численная ошибка: остаток кредита стал отрицательным")
		}

		remainingPrincipal := remaining
		if remainingPrincipal < 0 {
			remainingPrincipal = 0.0
		}

		schedule = append(schedule, ScheduleEntry{
			Month:               float64(m),
			Payment:             payment,
			Interest:            interest,
			PrincipalComponent:  principalComponent,
			RemainingPrincipal:  remainingPrincipal,
			CumulativeInterest:  cumI,
			CumulativePrincipal: cumP,
		})
	}

	summary := LoanSummary{
		Principal:         utils.Round2(P),
		AnnualRatePercent: utils.Round2(annualRatePercent),
		Months:            float64(n),
		FirstMonthPayment: firstPayment,
		LastMonthPayment:  lastPayment,
		TotalPaid:         totalPaid,
		TotalInterest:     cumI,
	}

	return &CalculationResult{
		Summary:  summary,
		Schedule: schedule,
	}, nil
}
