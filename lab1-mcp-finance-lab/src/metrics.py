"""Метрики Prometheus для MCP сервера."""

from prometheus_client import Counter

# Публичные метрики
TOOL_CALLS = Counter(
    "tool_calls_total",
    "Общее количество вызовов инструментов",
    ["tool_name", "status"],
)

CALCULATION_ERRORS = Counter(
    "calculation_errors_total",
    "Количество ошибок расчетов",
    ["tool_name", "error_type"],
)

API_CALLS = Counter(
    "api_calls_total",
    "Вызовы API инструментов",
    ["service", "endpoint", "status"],
)
