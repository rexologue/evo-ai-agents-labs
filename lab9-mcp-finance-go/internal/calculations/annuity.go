package calculations

import (
	"fmt"
	"math"

	"github.com/cloud-ru/mcp-finance-go/pkg/utils"
)

// AnnuitySchedule рассчитывает график аннуитетного кредита
func AnnuitySchedule(principal, annualRatePercent float64, months int) (*CalculationResult, error) {
	P := principal
	n := months
	r := annualRatePercent / 100.0 / 12.0

	schedule := make([]ScheduleEntry, 0, n)
	remaining := P
	cumI := 0.0
	cumP := 0.0

	var monthlyPayment float64
	if r == 0.0 {
		monthlyPayment = P / float64(n)
	} else {
		monthlyPayment = P * r / (1.0 - math.Pow(1.0+r, float64(-n)))
	}

	totalPaid := 0.0

	for m := 1; m <= n; m++ {
		var interest float64
		if r == 0.0 {
			interest = 0.0
		} else {
			interest = remaining * r
		}

		principalComponent := monthlyPayment - interest
		var monthly float64

		if m == n {
			principalComponent = remaining
			monthly = principalComponent + interest
		} else {
			monthly = monthlyPayment
		}

		interest = utils.Round2(interest)
		principalComponent = utils.Round2(principalComponent)
		monthly = utils.Round2(monthly)

		remaining = utils.Round2(remaining - principalComponent)
		cumI = utils.Round2(cumI + interest)
		cumP = utils.Round2(cumP + principalComponent)
		totalPaid = utils.Round2(totalPaid + monthly)

		if remaining < -0.01 {
			return nil, fmt.Errorf("численная ошибка: остаток кредита стал отрицательным")
		}

		remainingPrincipal := remaining
		if remainingPrincipal < 0 {
			remainingPrincipal = 0.0
		}

		schedule = append(schedule, ScheduleEntry{
			Month:               float64(m),
			Payment:             monthly,
			Interest:            interest,
			PrincipalComponent:  principalComponent,
			RemainingPrincipal:  remainingPrincipal,
			CumulativeInterest:  cumI,
			CumulativePrincipal: cumP,
		})
	}

	var finalMonthlyPayment float64
	if r == 0.0 {
		finalMonthlyPayment = P / float64(n)
	} else {
		finalMonthlyPayment = monthlyPayment
	}

	summary := LoanSummary{
		Principal:         utils.Round2(P),
		AnnualRatePercent: utils.Round2(annualRatePercent),
		Months:            float64(n),
		MonthlyPayment:    utils.Round2(finalMonthlyPayment),
		TotalPaid:         totalPaid,
		TotalInterest:     cumI,
	}

	return &CalculationResult{
		Summary:  summary,
		Schedule: schedule,
	}, nil
}
