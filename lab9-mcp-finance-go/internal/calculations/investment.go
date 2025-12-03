package calculations

import (
	"math"

	"github.com/cloud-ru/mcp-finance-go/pkg/utils"
)

// InvestmentCalculator рассчитывает рост инвестиций с регулярными взносами
func InvestmentCalculator(cfg ConfigInterface, initialAmount, annualRatePercent float64, months int,
	monthlyContribution float64, contributionAtBeginning bool) (*InvestmentResult, error) {

	// Используем существующую функцию deposit_schedule для расчета
	depositResult, err := DepositSchedule(cfg, initialAmount, annualRatePercent, months,
		monthlyContribution, contributionAtBeginning)
	if err != nil {
		return nil, err
	}

	depositSummary := depositResult.Summary.(DepositSummary)

	// Вычисляем дополнительные метрики для инвестиций
	finalBalance := depositSummary.FinalBalance
	totalContributions := depositSummary.TotalContributions
	totalInterest := depositSummary.TotalInterest
	initialInvestment := depositSummary.InitialAmount

	// ROI (Return on Investment) в процентах
	totalInvested := initialInvestment + totalContributions
	var roiPercent float64
	if totalInvested > 0 {
		roiPercent = utils.Round2(((finalBalance - totalInvested) / totalInvested) * 100)
	} else {
		roiPercent = 0.0
	}

	// Средняя годовая доходность
	years := float64(months) / 12.0
	var annualizedReturn float64
	if years > 0 {
		if initialInvestment > 0 {
			annualizedReturn = utils.Round2((math.Pow(finalBalance/totalInvested, 1.0/years) - 1.0) * 100)
		} else {
			annualizedReturn = 0.0
		}
	} else {
		annualizedReturn = 0.0
	}

	// Прирост капитала
	capitalGain := utils.Round2(finalBalance - totalInvested)

	// Процент от общей суммы, который составляет прибыль
	var profitPercent float64
	if finalBalance > 0 {
		profitPercent = utils.Round2((totalInterest / finalBalance) * 100)
	} else {
		profitPercent = 0.0
	}

	growthMetrics := GrowthMetrics{
		ROIPercent:              roiPercent,
		AnnualizedReturnPercent: annualizedReturn,
		CapitalGain:             capitalGain,
		ProfitPercent:           profitPercent,
		TotalInvested:           totalInvested,
		FinalValue:              finalBalance,
		Years:                   utils.Round2(years),
	}

	// Формируем итоговый summary с инвестиционными метриками
	investmentSummary := InvestmentSummary{
		DepositSummary:          depositSummary,
		ROIPercent:              roiPercent,
		AnnualizedReturnPercent: annualizedReturn,
		CapitalGain:             capitalGain,
		TotalInvested:           totalInvested,
	}

	return &InvestmentResult{
		Summary:       investmentSummary,
		Schedule:      depositResult.Schedule,
		GrowthMetrics: growthMetrics,
	}, nil
}
