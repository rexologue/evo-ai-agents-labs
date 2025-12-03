package validators

import (
	"testing"

	"github.com/cloud-ru/mcp-finance-go/internal/config"
)

func TestValidators(t *testing.T) {
	cfg, _ := config.LoadConfig()

	tests := []struct {
		name      string
		validator func(*config.Config, interface{}) error
		value     interface{}
		wantError bool
	}{
		{
			name:      "valid principal",
			validator: func(cfg *config.Config, v interface{}) error { return CheckPrincipal(cfg, v.(float64)) },
			value:     1000000.0,
			wantError: false,
		},
		{
			name:      "invalid principal zero",
			validator: func(cfg *config.Config, v interface{}) error { return CheckPrincipal(cfg, v.(float64)) },
			value:     0.0,
			wantError: true,
		},
		{
			name:      "invalid principal negative",
			validator: func(cfg *config.Config, v interface{}) error { return CheckPrincipal(cfg, v.(float64)) },
			value:     -1000.0,
			wantError: true,
		},
		{
			name:      "valid rate",
			validator: func(cfg *config.Config, v interface{}) error { return CheckRate(cfg, v.(float64)) },
			value:     12.0,
			wantError: false,
		},
		{
			name:      "invalid rate negative",
			validator: func(cfg *config.Config, v interface{}) error { return CheckRate(cfg, v.(float64)) },
			value:     -1.0,
			wantError: true,
		},
		{
			name:      "valid months",
			validator: func(cfg *config.Config, v interface{}) error { return CheckMonths(cfg, v.(int)) },
			value:     12,
			wantError: false,
		},
		{
			name:      "invalid months zero",
			validator: func(cfg *config.Config, v interface{}) error { return CheckMonths(cfg, v.(int)) },
			value:     0,
			wantError: true,
		},
		{
			name:      "valid initial amount",
			validator: func(cfg *config.Config, v interface{}) error { return CheckInitialAmount(cfg, v.(float64)) },
			value:     100000.0,
			wantError: false,
		},
		{
			name:      "valid contribution",
			validator: func(cfg *config.Config, v interface{}) error { return CheckContribution(cfg, v.(float64)) },
			value:     10000.0,
			wantError: false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := tt.validator(cfg, tt.value)
			if (err != nil) != tt.wantError {
				t.Errorf("validator error = %v, wantError %v", err, tt.wantError)
			}
		})
	}
}
