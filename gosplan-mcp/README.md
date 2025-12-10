

MCP endpoint: http://0.0.0.0:8000/mcp

    MCP/
    ├── src/
    │   ├── mcp_instance.py            # Единый экземпляр FastMCP
    │   ├── server.py                  # Главный файл запуска
    │   ├── tools/
    │   │   ├── __init__.py
    │   │   ├── tool_name.py            # Инструменты (один файл = один инструмент)
    │   │   ├── utils.py                # Общие утилиты
    │   │   └── models.py               # Pydantic модели (опционально)
    │   ├── middleware/
    │   │   ├── __init__.py
    │   │   └── custom_middleware.py    # Кастомные middleware (опционально)
    │   ├── utils/
    │   │   └── settings.py
    │   └── metrics.py                   # Prometheus метрики (опционально)
    ├── test/
    │   ├── __init__.py
    │   ├── test_tools.py           # Unit тесты инструментов
    │   └── test_integration.py     # Интеграционные тесты
    ├── pyproject.toml               # Зависимости проекта
    ├── .env.example                 # Пример переменных окружения
    ├── env_options.json             # Описание переменных окружения
    ├── mcp-server-catalog.yaml      # Каталог MCP сервера
    ├── mcp_tools.json               # JSON описание инструментов MCP
    ├── README.md                    # Документация проекта
    ├── Dockerfile                   # Docker образ
    └── docker-compose.yml           # Docker Compose конфигурация