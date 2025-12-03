package tools

import (
	"context"
	"fmt"

	"github.com/cloud-ru/mcp-finance-go/internal/calculations"
	"github.com/cloud-ru/mcp-finance-go/internal/config"
	"github.com/cloud-ru/mcp-finance-go/internal/metrics"
	"github.com/cloud-ru/mcp-finance-go/internal/validators"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/trace"
)

// ToolHandler представляет обработчик инструмента MCP
type ToolHandler func(ctx context.Context, params map[string]interface{}) (interface{}, error)

// LoanScheduleAnnuityHandler обрабатывает запрос на расчет аннуитетного кредита
func LoanScheduleAnnuityHandler(cfg *config.Config, tracer trace.Tracer) ToolHandler {
	return func(ctx context.Context, params map[string]interface{}) (interface{}, error) {
		toolName := "loan_schedule_annuity"

		ctx, span := tracer.Start(ctx, toolName)
		defer span.End()

		// Извлекаем параметры
		principal, ok := params["principal"].(float64)
		if !ok {
			return nil, fmt.Errorf("invalid parameter: principal")
		}
		annualRatePercent, ok := params["annual_rate_percent"].(float64)
		if !ok {
			return nil, fmt.Errorf("invalid parameter: annual_rate_percent")
		}
		monthsFloat, ok := params["months"].(float64)
		if !ok {
			return nil, fmt.Errorf("invalid parameter: months")
		}
		months := int(monthsFloat)

		span.SetAttributes(
			attribute.Float64("principal", principal),
			attribute.Float64("annual_rate_percent", annualRatePercent),
			attribute.Int("months", months),
		)

		metrics.APICalls.WithLabelValues("mcp", toolName, "started").Inc()

		// Валидация
		if err := validators.CheckPrincipal(cfg, principal); err != nil {
			span.SetAttributes(attribute.String("error", "validation_error"))
			metrics.ToolCalls.WithLabelValues(toolName, "validation_error").Inc()
			metrics.CalculationErrors.WithLabelValues(toolName, "validation").Inc()
			metrics.APICalls.WithLabelValues("mcp", toolName, "error").Inc()
			return nil, fmt.Errorf("неверные параметры: %w", err)
		}
		if err := validators.CheckRate(cfg, annualRatePercent); err != nil {
			span.SetAttributes(attribute.String("error", "validation_error"))
			metrics.ToolCalls.WithLabelValues(toolName, "validation_error").Inc()
			metrics.CalculationErrors.WithLabelValues(toolName, "validation").Inc()
			metrics.APICalls.WithLabelValues("mcp", toolName, "error").Inc()
			return nil, fmt.Errorf("неверные параметры: %w", err)
		}
		if err := validators.CheckMonths(cfg, months); err != nil {
			span.SetAttributes(attribute.String("error", "validation_error"))
			metrics.ToolCalls.WithLabelValues(toolName, "validation_error").Inc()
			metrics.CalculationErrors.WithLabelValues(toolName, "validation").Inc()
			metrics.APICalls.WithLabelValues("mcp", toolName, "error").Inc()
			return nil, fmt.Errorf("неверные параметры: %w", err)
		}

		// Расчет
		result, err := calculations.AnnuitySchedule(principal, annualRatePercent, months)
		if err != nil {
			span.SetAttributes(attribute.String("error", "calculation_error"))
			metrics.ToolCalls.WithLabelValues(toolName, "error").Inc()
			metrics.CalculationErrors.WithLabelValues(toolName, "calculation").Inc()
			metrics.APICalls.WithLabelValues("mcp", toolName, "error").Inc()
			return nil, fmt.Errorf("ошибка при выполнении расчета: %w", err)
		}

		// Преобразуем summary для получения значений
		if summary, ok := result.Summary.(calculations.LoanSummary); ok {
			span.SetAttributes(
				attribute.Bool("success", true),
				attribute.Float64("monthly_payment", summary.MonthlyPayment),
				attribute.Float64("total_paid", summary.TotalPaid),
			)
		} else {
			span.SetAttributes(attribute.Bool("success", true))
		}

		metrics.ToolCalls.WithLabelValues(toolName, "success").Inc()
		metrics.APICalls.WithLabelValues("mcp", toolName, "success").Inc()

		return result, nil
	}
}

// LoanScheduleDifferentialHandler обрабатывает запрос на расчет дифференцированного кредита
func LoanScheduleDifferentialHandler(cfg *config.Config, tracer trace.Tracer) ToolHandler {
	return func(ctx context.Context, params map[string]interface{}) (interface{}, error) {
		toolName := "loan_schedule_differential"

		ctx, span := tracer.Start(ctx, toolName)
		defer span.End()

		principal, ok := params["principal"].(float64)
		if !ok {
			return nil, fmt.Errorf("invalid parameter: principal")
		}
		annualRatePercent, ok := params["annual_rate_percent"].(float64)
		if !ok {
			return nil, fmt.Errorf("invalid parameter: annual_rate_percent")
		}
		monthsFloat, ok := params["months"].(float64)
		if !ok {
			return nil, fmt.Errorf("invalid parameter: months")
		}
		months := int(monthsFloat)

		span.SetAttributes(
			attribute.Float64("principal", principal),
			attribute.Float64("annual_rate_percent", annualRatePercent),
			attribute.Int("months", months),
		)

		metrics.APICalls.WithLabelValues("mcp", toolName, "started").Inc()

		if err := validators.CheckPrincipal(cfg, principal); err != nil {
			span.SetAttributes(attribute.String("error", "validation_error"))
			metrics.ToolCalls.WithLabelValues(toolName, "validation_error").Inc()
			metrics.CalculationErrors.WithLabelValues(toolName, "validation").Inc()
			metrics.APICalls.WithLabelValues("mcp", toolName, "error").Inc()
			return nil, fmt.Errorf("неверные параметры: %w", err)
		}
		if err := validators.CheckRate(cfg, annualRatePercent); err != nil {
			span.SetAttributes(attribute.String("error", "validation_error"))
			metrics.ToolCalls.WithLabelValues(toolName, "validation_error").Inc()
			metrics.CalculationErrors.WithLabelValues(toolName, "validation").Inc()
			metrics.APICalls.WithLabelValues("mcp", toolName, "error").Inc()
			return nil, fmt.Errorf("неверные параметры: %w", err)
		}
		if err := validators.CheckMonths(cfg, months); err != nil {
			span.SetAttributes(attribute.String("error", "validation_error"))
			metrics.ToolCalls.WithLabelValues(toolName, "validation_error").Inc()
			metrics.CalculationErrors.WithLabelValues(toolName, "validation").Inc()
			metrics.APICalls.WithLabelValues("mcp", toolName, "error").Inc()
			return nil, fmt.Errorf("неверные параметры: %w", err)
		}

		result, err := calculations.DifferentialSchedule(principal, annualRatePercent, months)
		if err != nil {
			span.SetAttributes(attribute.String("error", "calculation_error"))
			metrics.ToolCalls.WithLabelValues(toolName, "error").Inc()
			metrics.CalculationErrors.WithLabelValues(toolName, "calculation").Inc()
			metrics.APICalls.WithLabelValues("mcp", toolName, "error").Inc()
			return nil, fmt.Errorf("ошибка при выполнении расчета: %w", err)
		}

		span.SetAttributes(attribute.Bool("success", true))
		metrics.ToolCalls.WithLabelValues(toolName, "success").Inc()
		metrics.APICalls.WithLabelValues("mcp", toolName, "success").Inc()

		return result, nil
	}
}

// DepositScheduleCompoundHandler обрабатывает запрос на расчет вклада
func DepositScheduleCompoundHandler(cfg *config.Config, tracer trace.Tracer) ToolHandler {
	return func(ctx context.Context, params map[string]interface{}) (interface{}, error) {
		toolName := "deposit_schedule_compound"

		ctx, span := tracer.Start(ctx, toolName)
		defer span.End()

		initialAmount, ok := params["initial_amount"].(float64)
		if !ok {
			return nil, fmt.Errorf("invalid parameter: initial_amount")
		}
		annualRatePercent, ok := params["annual_rate_percent"].(float64)
		if !ok {
			return nil, fmt.Errorf("invalid parameter: annual_rate_percent")
		}
		monthsFloat, ok := params["months"].(float64)
		if !ok {
			return nil, fmt.Errorf("invalid parameter: months")
		}
		months := int(monthsFloat)
		monthlyContribution, ok := params["monthly_contribution"].(float64)
		if !ok {
			return nil, fmt.Errorf("invalid parameter: monthly_contribution")
		}
		contributionAtBeginning, ok := params["contribution_at_beginning"].(bool)
		if !ok {
			return nil, fmt.Errorf("invalid parameter: contribution_at_beginning")
		}

		span.SetAttributes(
			attribute.Float64("initial_amount", initialAmount),
			attribute.Float64("annual_rate_percent", annualRatePercent),
			attribute.Int("months", months),
			attribute.Float64("monthly_contribution", monthlyContribution),
			attribute.Bool("contribution_at_beginning", contributionAtBeginning),
		)

		metrics.APICalls.WithLabelValues("mcp", toolName, "started").Inc()

		if err := validators.CheckInitialAmount(cfg, initialAmount); err != nil {
			span.SetAttributes(attribute.String("error", "validation_error"))
			metrics.ToolCalls.WithLabelValues(toolName, "validation_error").Inc()
			metrics.CalculationErrors.WithLabelValues(toolName, "validation").Inc()
			metrics.APICalls.WithLabelValues("mcp", toolName, "error").Inc()
			return nil, fmt.Errorf("неверные параметры: %w", err)
		}
		if err := validators.CheckRate(cfg, annualRatePercent); err != nil {
			span.SetAttributes(attribute.String("error", "validation_error"))
			metrics.ToolCalls.WithLabelValues(toolName, "validation_error").Inc()
			metrics.CalculationErrors.WithLabelValues(toolName, "validation").Inc()
			metrics.APICalls.WithLabelValues("mcp", toolName, "error").Inc()
			return nil, fmt.Errorf("неверные параметры: %w", err)
		}
		if err := validators.CheckMonths(cfg, months); err != nil {
			span.SetAttributes(attribute.String("error", "validation_error"))
			metrics.ToolCalls.WithLabelValues(toolName, "validation_error").Inc()
			metrics.CalculationErrors.WithLabelValues(toolName, "validation").Inc()
			metrics.APICalls.WithLabelValues("mcp", toolName, "error").Inc()
			return nil, fmt.Errorf("неверные параметры: %w", err)
		}
		if err := validators.CheckContribution(cfg, monthlyContribution); err != nil {
			span.SetAttributes(attribute.String("error", "validation_error"))
			metrics.ToolCalls.WithLabelValues(toolName, "validation_error").Inc()
			metrics.CalculationErrors.WithLabelValues(toolName, "validation").Inc()
			metrics.APICalls.WithLabelValues("mcp", toolName, "error").Inc()
			return nil, fmt.Errorf("неверные параметры: %w", err)
		}

		result, err := calculations.DepositSchedule(cfg, initialAmount, annualRatePercent, months,
			monthlyContribution, contributionAtBeginning)
		if err != nil {
			span.SetAttributes(attribute.String("error", "calculation_error"))
			metrics.ToolCalls.WithLabelValues(toolName, "error").Inc()
			metrics.CalculationErrors.WithLabelValues(toolName, "calculation").Inc()
			metrics.APICalls.WithLabelValues("mcp", toolName, "error").Inc()
			return nil, fmt.Errorf("ошибка при выполнении расчета: %w", err)
		}

		span.SetAttributes(attribute.Bool("success", true))
		metrics.ToolCalls.WithLabelValues(toolName, "success").Inc()
		metrics.APICalls.WithLabelValues("mcp", toolName, "success").Inc()

		return result, nil
	}
}

// CompareLoanSchedulesHandler обрабатывает запрос на сравнение кредитов
func CompareLoanSchedulesHandler(cfg *config.Config, tracer trace.Tracer) ToolHandler {
	return func(ctx context.Context, params map[string]interface{}) (interface{}, error) {
		toolName := "compare_loan_schedules"

		ctx, span := tracer.Start(ctx, toolName)
		defer span.End()

		principal, ok := params["principal"].(float64)
		if !ok {
			return nil, fmt.Errorf("invalid parameter: principal")
		}
		annualRatePercent, ok := params["annual_rate_percent"].(float64)
		if !ok {
			return nil, fmt.Errorf("invalid parameter: annual_rate_percent")
		}
		monthsFloat, ok := params["months"].(float64)
		if !ok {
			return nil, fmt.Errorf("invalid parameter: months")
		}
		months := int(monthsFloat)

		span.SetAttributes(
			attribute.Float64("principal", principal),
			attribute.Float64("annual_rate_percent", annualRatePercent),
			attribute.Int("months", months),
		)

		metrics.APICalls.WithLabelValues("mcp", toolName, "started").Inc()

		if err := validators.CheckPrincipal(cfg, principal); err != nil {
			span.SetAttributes(attribute.String("error", "validation_error"))
			metrics.ToolCalls.WithLabelValues(toolName, "validation_error").Inc()
			metrics.CalculationErrors.WithLabelValues(toolName, "validation").Inc()
			metrics.APICalls.WithLabelValues("mcp", toolName, "error").Inc()
			return nil, fmt.Errorf("неверные параметры: %w", err)
		}
		if err := validators.CheckRate(cfg, annualRatePercent); err != nil {
			span.SetAttributes(attribute.String("error", "validation_error"))
			metrics.ToolCalls.WithLabelValues(toolName, "validation_error").Inc()
			metrics.CalculationErrors.WithLabelValues(toolName, "validation").Inc()
			metrics.APICalls.WithLabelValues("mcp", toolName, "error").Inc()
			return nil, fmt.Errorf("неверные параметры: %w", err)
		}
		if err := validators.CheckMonths(cfg, months); err != nil {
			span.SetAttributes(attribute.String("error", "validation_error"))
			metrics.ToolCalls.WithLabelValues(toolName, "validation_error").Inc()
			metrics.CalculationErrors.WithLabelValues(toolName, "validation").Inc()
			metrics.APICalls.WithLabelValues("mcp", toolName, "error").Inc()
			return nil, fmt.Errorf("неверные параметры: %w", err)
		}

		result, err := calculations.CompareLoans(principal, annualRatePercent, months)
		if err != nil {
			span.SetAttributes(attribute.String("error", "calculation_error"))
			metrics.ToolCalls.WithLabelValues(toolName, "error").Inc()
			metrics.CalculationErrors.WithLabelValues(toolName, "calculation").Inc()
			metrics.APICalls.WithLabelValues("mcp", toolName, "error").Inc()
			return nil, fmt.Errorf("ошибка при выполнении расчета: %w", err)
		}

		span.SetAttributes(attribute.Bool("success", true))
		metrics.ToolCalls.WithLabelValues(toolName, "success").Inc()
		metrics.APICalls.WithLabelValues("mcp", toolName, "success").Inc()

		return result, nil
	}
}

// InvestmentCalculatorHandler обрабатывает запрос на расчет инвестиций
func InvestmentCalculatorHandler(cfg *config.Config, tracer trace.Tracer) ToolHandler {
	return func(ctx context.Context, params map[string]interface{}) (interface{}, error) {
		toolName := "investment_calculator"

		ctx, span := tracer.Start(ctx, toolName)
		defer span.End()

		initialAmount, ok := params["initial_amount"].(float64)
		if !ok {
			return nil, fmt.Errorf("invalid parameter: initial_amount")
		}
		annualRatePercent, ok := params["annual_rate_percent"].(float64)
		if !ok {
			return nil, fmt.Errorf("invalid parameter: annual_rate_percent")
		}
		monthsFloat, ok := params["months"].(float64)
		if !ok {
			return nil, fmt.Errorf("invalid parameter: months")
		}
		months := int(monthsFloat)
		monthlyContribution, ok := params["monthly_contribution"].(float64)
		if !ok {
			return nil, fmt.Errorf("invalid parameter: monthly_contribution")
		}
		contributionAtBeginning, ok := params["contribution_at_beginning"].(bool)
		if !ok {
			return nil, fmt.Errorf("invalid parameter: contribution_at_beginning")
		}

		span.SetAttributes(
			attribute.Float64("initial_amount", initialAmount),
			attribute.Float64("annual_rate_percent", annualRatePercent),
			attribute.Int("months", months),
			attribute.Float64("monthly_contribution", monthlyContribution),
			attribute.Bool("contribution_at_beginning", contributionAtBeginning),
		)

		metrics.APICalls.WithLabelValues("mcp", toolName, "started").Inc()

		if err := validators.CheckInitialAmount(cfg, initialAmount); err != nil {
			span.SetAttributes(attribute.String("error", "validation_error"))
			metrics.ToolCalls.WithLabelValues(toolName, "validation_error").Inc()
			metrics.CalculationErrors.WithLabelValues(toolName, "validation").Inc()
			metrics.APICalls.WithLabelValues("mcp", toolName, "error").Inc()
			return nil, fmt.Errorf("неверные параметры: %w", err)
		}
		if err := validators.CheckRate(cfg, annualRatePercent); err != nil {
			span.SetAttributes(attribute.String("error", "validation_error"))
			metrics.ToolCalls.WithLabelValues(toolName, "validation_error").Inc()
			metrics.CalculationErrors.WithLabelValues(toolName, "validation").Inc()
			metrics.APICalls.WithLabelValues("mcp", toolName, "error").Inc()
			return nil, fmt.Errorf("неверные параметры: %w", err)
		}
		if err := validators.CheckMonths(cfg, months); err != nil {
			span.SetAttributes(attribute.String("error", "validation_error"))
			metrics.ToolCalls.WithLabelValues(toolName, "validation_error").Inc()
			metrics.CalculationErrors.WithLabelValues(toolName, "validation").Inc()
			metrics.APICalls.WithLabelValues("mcp", toolName, "error").Inc()
			return nil, fmt.Errorf("неверные параметры: %w", err)
		}
		if err := validators.CheckContribution(cfg, monthlyContribution); err != nil {
			span.SetAttributes(attribute.String("error", "validation_error"))
			metrics.ToolCalls.WithLabelValues(toolName, "validation_error").Inc()
			metrics.CalculationErrors.WithLabelValues(toolName, "validation").Inc()
			metrics.APICalls.WithLabelValues("mcp", toolName, "error").Inc()
			return nil, fmt.Errorf("неверные параметры: %w", err)
		}

		result, err := calculations.InvestmentCalculator(cfg, initialAmount, annualRatePercent, months,
			monthlyContribution, contributionAtBeginning)
		if err != nil {
			span.SetAttributes(attribute.String("error", "calculation_error"))
			metrics.ToolCalls.WithLabelValues(toolName, "error").Inc()
			metrics.CalculationErrors.WithLabelValues(toolName, "calculation").Inc()
			metrics.APICalls.WithLabelValues("mcp", toolName, "error").Inc()
			return nil, fmt.Errorf("ошибка при выполнении расчета: %w", err)
		}

		span.SetAttributes(attribute.Bool("success", true))
		metrics.ToolCalls.WithLabelValues(toolName, "success").Inc()
		metrics.APICalls.WithLabelValues("mcp", toolName, "success").Inc()

		return result, nil
	}
}
