package utils

import "math"

// Round2 округляет число до 2 знаков после запятой
func Round2(value float64) float64 {
	return math.Round(value*100) / 100
}

// IsFinite проверяет, является ли число конечным
func IsFinite(value float64) bool {
	return !math.IsInf(value, 0) && !math.IsNaN(value)
}
