package tracing

import (
	"context"
	"fmt"
	"os"

	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracehttp"
	"go.opentelemetry.io/otel/sdk/resource"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
	semconv "go.opentelemetry.io/otel/semconv/v1.24.0"
	"go.opentelemetry.io/otel/trace"
)

var Tracer trace.Tracer

// InitTracing инициализирует OpenTelemetry трейсинг
func InitTracing(serviceName string) error {
	otelEndpoint := os.Getenv("OTEL_ENDPOINT")

	res, err := resource.New(context.Background(),
		resource.WithAttributes(
			semconv.ServiceNameKey.String(serviceName),
			semconv.ServiceVersionKey.String("1.0.0"),
		),
	)
	if err != nil {
		return fmt.Errorf("failed to create resource: %w", err)
	}

	var exporter sdktrace.SpanExporter

	if otelEndpoint != "" {
		// Используем OTLP HTTP экспортер
		exporter, err = otlptracehttp.New(context.Background(),
			otlptracehttp.WithEndpoint(otelEndpoint),
		)
		if err != nil {
			return fmt.Errorf("failed to create OTLP exporter: %w", err)
		}
		fmt.Printf("✅ OpenTelemetry настроен для OTLP экспорта: %s\n", otelEndpoint)
	} else {
		// Используем noop экспортер для локальной разработки
		// В продакшене рекомендуется использовать OTLP
		fmt.Println("✅ OpenTelemetry настроен (используйте OTEL_ENDPOINT для экспорта)")
		// Создаем noop exporter, если нет endpoint
		exporter = &noopExporter{}
	}

	tp := sdktrace.NewTracerProvider(
		sdktrace.WithBatcher(exporter),
		sdktrace.WithResource(res),
	)

	otel.SetTracerProvider(tp)
	Tracer = otel.Tracer(serviceName)

	fmt.Println("✅ OpenTelemetry инициализирован")
	return nil
}

// noopExporter - пустой экспортер для локальной разработки
type noopExporter struct{}

func (e *noopExporter) ExportSpans(ctx context.Context, spans []sdktrace.ReadWriteSpan) error {
	return nil
}

func (e *noopExporter) Shutdown(ctx context.Context) error {
	return nil
}
