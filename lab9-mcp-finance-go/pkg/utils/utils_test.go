package utils

import (
	"math"
	"testing"
)

func TestRound2(t *testing.T) {
	tests := []struct {
		name  string
		input float64
		want  float64
	}{
		{
			name:  "round to 2 decimals",
			input: 123.456789,
			want:  123.46,
		},
		{
			name:  "already 2 decimals",
			input: 123.45,
			want:  123.45,
		},
		{
			name:  "integer",
			input: 123.0,
			want:  123.0,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := Round2(tt.input)
			if math.Abs(got-tt.want) > 0.01 {
				t.Errorf("Round2() = %v, want %v", got, tt.want)
			}
		})
	}
}

func TestIsFinite(t *testing.T) {
	tests := []struct {
		name  string
		input float64
		want  bool
	}{
		{
			name:  "finite number",
			input: 123.45,
			want:  true,
		},
		{
			name:  "infinity",
			input: math.Inf(1),
			want:  false,
		},
		{
			name:  "negative infinity",
			input: math.Inf(-1),
			want:  false,
		},
		{
			name:  "NaN",
			input: math.NaN(),
			want:  false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := IsFinite(tt.input)
			if got != tt.want {
				t.Errorf("IsFinite() = %v, want %v", got, tt.want)
			}
		})
	}
}
