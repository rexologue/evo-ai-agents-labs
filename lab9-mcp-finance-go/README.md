# MCP Finance Server (Go)

MCP сервер для финансовых расчетов на языке Go. Предоставляет инструменты для расчета графиков платежей по кредитам, вкладам с капитализацией и инвестициям с регулярными взносами.

## Возможности

Сервер предоставляет 5 инструментов:

1. **loan_schedule_annuity** - Расчет аннуитетного кредита
2. **loan_schedule_differential** - Расчет дифференцированного кредита
3. **deposit_schedule_compound** - Расчет вклада с капитализацией
4. **compare_loan_schedules** - Сравнение типов кредитов
5. **investment_calculator** - Калькулятор инвестиций

## Требования

- Go >= 1.21
- Docker (опционально, для контейнеризации)

## Установка

### Локальная установка

1. Клонируйте репозиторий:
```bash
git clone <repository-url>
cd lab9-mcp-finance-go
```

2. Установите зависимости:
```bash
go mod download
```

3. Соберите приложение:
```bash
go build -o server ./cmd/server
```

4. Создайте файл `.env` (опционально):
```bash
cp .env.example .env
# Отредактируйте .env при необходимости
```

5. Запустите сервер:
```bash
./server
# или
go run ./cmd/server
```

### Docker

1. Соберите образ:
```bash
docker build -t mcp-finance-server-go .
```

2. Запустите контейнер:
```bash
docker run -p 8000:8000 \
  -e PORT=8000 \
  mcp-finance-server-go
```

## Использование

После запуска сервер будет доступен на:

- **MCP Server**: `http://localhost:8000/mcp` (JSON-RPC endpoint)
- **Метрики**: `http://localhost:8000/metrics` (Prometheus)
- **Health Check**: `http://localhost:8000/health`

### Пример запроса

```bash
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "loan_schedule_annuity",
    "params": {
      "principal": 1000000,
      "annual_rate_percent": 12,
      "months": 12
    }
  }'
```

## Переменные окружения

- `PORT` - Порт для запуска сервера (по умолчанию: 8000)
- `OTEL_ENDPOINT` - Endpoint для OpenTelemetry трейсинга (опционально)
- `OTEL_SERVICE_NAME` - Имя сервиса для трейсинга (по умолчанию: mcp-finance-server)
- `LOG_LEVEL` - Уровень логирования (по умолчанию: INFO)
- `MAX_PRINCIPAL` - Максимальная сумма кредита/вклада (по умолчанию: 1e9)
- `MAX_CONTRIBUTION` - Максимальный ежемесячный взнос (по умолчанию: 1e8)
- `MAX_MONTHS` - Максимальный срок в месяцах (по умолчанию: 600)
- `MAX_RATE` - Максимальная процентная ставка (по умолчанию: 200)
- `MAX_BALANCE_CAP` - Максимальный баланс (по умолчанию: 1e12)

Подробное описание всех переменных см. в `env_options.json`.

## Структура проекта

```
lab9-mcp-finance-go/
├── cmd/
│   └── server/
│       └── main.go              # Точка входа
├── internal/
│   ├── calculations/           # Бизнес-логика расчетов
│   ├── validators/              # Валидация параметров
│   ├── tools/                  # Обработчики MCP инструментов
│   ├── config/                 # Конфигурация
│   ├── metrics/                # Prometheus метрики
│   └── tracing/                # OpenTelemetry трейсинг
├── pkg/
│   └── utils/                  # Утилиты
├── Dockerfile
├── go.mod
└── README.md
```

## Метрики

Сервер предоставляет метрики Prometheus:

- `tool_calls_total` - Количество вызовов инструментов (labels: tool_name, status)
- `calculation_errors_total` - Количество ошибок расчетов (labels: tool_name, error_type)
- `api_calls_total` - Вызовы API (labels: service, endpoint, status)

## Трейсинг

Поддержка OpenTelemetry для распределенного трейсинга. Настройте `OTEL_ENDPOINT` для экспорта трейсов в продакшене.

## Тестирование

Запуск тестов:
```bash
go test ./...
```

## Лицензия

MIT

## Автор

ermadatov@cloud.ru
