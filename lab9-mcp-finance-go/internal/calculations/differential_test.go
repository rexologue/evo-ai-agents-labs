package calculations

import (
	"testing"
)

func TestDifferentialSchedule(t *testing.T) {
	result, err := DifferentialSchedule(1000000, 12, 12)
	if err != nil {
		t.Fatalf("DifferentialSchedule() error = %v", err)
	}

	if len(result.Schedule) != 12 {
		t.Errorf("expected 12 months, got %d", len(result.Schedule))
	}

	summary := result.Summary.(LoanSummary)
	if summary.FirstMonthPayment <= summary.LastMonthPayment {
		t.Error("first month payment should be greater than last month payment")
	}

	if summary.TotalPaid <= summary.Principal {
		t.Error("total paid should be greater than principal")
	}

	// Проверяем, что остаток в последнем месяце равен 0
	lastMonth := result.Schedule[len(result.Schedule)-1]
	if lastMonth.RemainingPrincipal != 0 {
		t.Errorf("expected remaining principal 0, got %f", lastMonth.RemainingPrincipal)
	}
}
