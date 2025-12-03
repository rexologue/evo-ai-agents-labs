package calculations

import (
	"fmt"

	"github.com/cloud-ru/mcp-finance-go/pkg/utils"
)

// ConfigInterface определяет интерфейс для получения конфигурации
type ConfigInterface interface {
	BalanceCap() float64
}

// DepositSchedule рассчитывает график вклада с капитализацией
func DepositSchedule(cfg ConfigInterface, initialAmount, annualRatePercent float64, months int,
	monthlyContribution float64, contributionAtBeginning bool) (*CalculationResult, error) {

	balance := initialAmount
	r := annualRatePercent / 100.0 / 12.0
	n := months
	contrib := monthlyContribution

	schedule := make([]ScheduleEntry, 0, n)
	cumI := 0.0
	cumC := 0.0

	// Получаем баланс кап из конфигурации
	cap := cfg.BalanceCap()

	for m := 1; m <= n; m++ {
		starting := balance

		if contributionAtBeginning {
			balance = utils.Round2(balance + contrib)
			cumC = utils.Round2(cumC + contrib)
		}

		interest := utils.Round2(balance * r)
		balance = utils.Round2(balance + interest)
		cumI = utils.Round2(cumI + interest)

		if !contributionAtBeginning {
			balance = utils.Round2(balance + contrib)
			cumC = utils.Round2(cumC + contrib)
		}

		if balance > cap {
			return nil, fmt.Errorf("итоговый баланс превысил верхнюю границу (проверьте ставку/срок/взносы)")
		}

		schedule = append(schedule, ScheduleEntry{
			Month:                   float64(m),
			StartingBalance:         utils.Round2(starting),
			Contribution:            utils.Round2(contrib),
			InterestEarned:          interest,
			EndingBalance:           utils.Round2(balance),
			CumulativeContributions: cumC,
			CumulativeInterest:      cumI,
		})
	}

	var contributionAtBeginningFloat float64
	if contributionAtBeginning {
		contributionAtBeginningFloat = 1.0
	} else {
		contributionAtBeginningFloat = 0.0
	}

	summary := DepositSummary{
		InitialAmount:           utils.Round2(initialAmount),
		AnnualRatePercent:       utils.Round2(annualRatePercent),
		Months:                  float64(n),
		MonthlyContribution:     utils.Round2(contrib),
		ContributionAtBeginning: contributionAtBeginningFloat,
		FinalBalance:            utils.Round2(balance),
		TotalContributions:      cumC,
		TotalInterest:           cumI,
	}

	return &CalculationResult{
		Summary:  summary,
		Schedule: schedule,
	}, nil
}
