package metrics

import (
	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
)

var (
	// ToolCalls счетчик вызовов инструментов
	ToolCalls = promauto.NewCounterVec(
		prometheus.CounterOpts{
			Name: "tool_calls_total",
			Help: "Общее количество вызовов инструментов",
		},
		[]string{"tool_name", "status"},
	)

	// CalculationErrors счетчик ошибок расчетов
	CalculationErrors = promauto.NewCounterVec(
		prometheus.CounterOpts{
			Name: "calculation_errors_total",
			Help: "Количество ошибок расчетов",
		},
		[]string{"tool_name", "error_type"},
	)

	// APICalls счетчик вызовов API
	APICalls = promauto.NewCounterVec(
		prometheus.CounterOpts{
			Name: "api_calls_total",
			Help: "Вызовы API инструментов",
		},
		[]string{"service", "endpoint", "status"},
	)
)
