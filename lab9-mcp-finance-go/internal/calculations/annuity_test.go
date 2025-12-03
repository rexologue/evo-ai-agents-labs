package calculations

import (
	"testing"
)

func TestAnnuitySchedule(t *testing.T) {
	tests := []struct {
		name              string
		principal         float64
		annualRatePercent float64
		months            int
		wantError         bool
		checkSummary      func(*testing.T, *CalculationResult)
	}{
		{
			name:              "basic annuity",
			principal:         1000000,
			annualRatePercent: 12,
			months:            12,
			wantError:         false,
			checkSummary: func(t *testing.T, result *CalculationResult) {
				if result == nil {
					t.Fatal("result is nil")
				}
				if len(result.Schedule) != 12 {
					t.Errorf("expected 12 months, got %d", len(result.Schedule))
				}
				summary := result.Summary.(LoanSummary)
				if summary.Principal != 1000000 {
					t.Errorf("expected principal 1000000, got %f", summary.Principal)
				}
				if summary.MonthlyPayment <= 0 {
					t.Error("monthly payment should be positive")
				}
				if summary.TotalPaid <= summary.Principal {
					t.Error("total paid should be greater than principal")
				}
				// Проверяем, что остаток в последнем месяце равен 0
				lastMonth := result.Schedule[len(result.Schedule)-1]
				if lastMonth.RemainingPrincipal != 0 {
					t.Errorf("expected remaining principal 0, got %f", lastMonth.RemainingPrincipal)
				}
			},
		},
		{
			name:              "zero rate",
			principal:         100000,
			annualRatePercent: 0,
			months:            10,
			wantError:         false,
			checkSummary: func(t *testing.T, result *CalculationResult) {
				summary := result.Summary.(LoanSummary)
				if summary.MonthlyPayment != 10000 {
					t.Errorf("expected monthly payment 10000, got %f", summary.MonthlyPayment)
				}
				if summary.TotalInterest != 0 {
					t.Errorf("expected total interest 0, got %f", summary.TotalInterest)
				}
			},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result, err := AnnuitySchedule(tt.principal, tt.annualRatePercent, tt.months)
			if (err != nil) != tt.wantError {
				t.Errorf("AnnuitySchedule() error = %v, wantError %v", err, tt.wantError)
				return
			}
			if !tt.wantError && tt.checkSummary != nil {
				tt.checkSummary(t, result)
			}
		})
	}
}
