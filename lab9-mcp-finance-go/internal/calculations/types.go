package calculations

// ScheduleEntry представляет одну запись в графике платежей
type ScheduleEntry struct {
	Month                   float64 `json:"month"`
	Payment                 float64 `json:"payment,omitempty"`
	Interest                float64 `json:"interest,omitempty"`
	PrincipalComponent      float64 `json:"principal_component,omitempty"`
	RemainingPrincipal      float64 `json:"remaining_principal,omitempty"`
	CumulativeInterest      float64 `json:"cumulative_interest,omitempty"`
	CumulativePrincipal     float64 `json:"cumulative_principal,omitempty"`
	StartingBalance         float64 `json:"starting_balance,omitempty"`
	Contribution            float64 `json:"contribution,omitempty"`
	InterestEarned          float64 `json:"interest_earned,omitempty"`
	EndingBalance           float64 `json:"ending_balance,omitempty"`
	CumulativeContributions float64 `json:"cumulative_contributions,omitempty"`
}

// LoanSummary представляет сводку по кредиту
type LoanSummary struct {
	Principal         float64 `json:"principal"`
	AnnualRatePercent float64 `json:"annual_rate_percent"`
	Months            float64 `json:"months"`
	MonthlyPayment    float64 `json:"monthly_payment,omitempty"`
	FirstMonthPayment float64 `json:"first_month_payment,omitempty"`
	LastMonthPayment  float64 `json:"last_month_payment,omitempty"`
	TotalPaid         float64 `json:"total_paid"`
	TotalInterest     float64 `json:"total_interest"`
}

// DepositSummary представляет сводку по вкладу
type DepositSummary struct {
	InitialAmount           float64 `json:"initial_amount"`
	AnnualRatePercent       float64 `json:"annual_rate_percent"`
	Months                  float64 `json:"months"`
	MonthlyContribution     float64 `json:"monthly_contribution"`
	ContributionAtBeginning float64 `json:"contribution_at_beginning"`
	FinalBalance            float64 `json:"final_balance"`
	TotalContributions      float64 `json:"total_contributions"`
	TotalInterest           float64 `json:"total_interest"`
}

// InvestmentSummary представляет сводку по инвестициям
type InvestmentSummary struct {
	DepositSummary
	ROIPercent              float64 `json:"roi_percent"`
	AnnualizedReturnPercent float64 `json:"annualized_return_percent"`
	CapitalGain             float64 `json:"capital_gain"`
	TotalInvested           float64 `json:"total_invested"`
}

// GrowthMetrics представляет метрики роста инвестиций
type GrowthMetrics struct {
	ROIPercent              float64 `json:"roi_percent"`
	AnnualizedReturnPercent float64 `json:"annualized_return_percent"`
	CapitalGain             float64 `json:"capital_gain"`
	ProfitPercent           float64 `json:"profit_percent,omitempty"`
	TotalInvested           float64 `json:"total_invested"`
	FinalValue              float64 `json:"final_value"`
	Years                   float64 `json:"years"`
}

// CalculationResult представляет результат расчета кредита/вклада
type CalculationResult struct {
	Summary  interface{}     `json:"summary"`
	Schedule []ScheduleEntry `json:"schedule"`
}

// ComparisonResult представляет результат сравнения кредитов
type ComparisonResult struct {
	Comparison   map[string]interface{} `json:"comparison"`
	Annuity      CalculationResult      `json:"annuity"`
	Differential CalculationResult      `json:"differential"`
}

// InvestmentResult представляет результат расчета инвестиций
type InvestmentResult struct {
	Summary       InvestmentSummary `json:"summary"`
	Schedule      []ScheduleEntry   `json:"schedule"`
	GrowthMetrics GrowthMetrics     `json:"growth_metrics"`
}
