# Лабораторная работа 6: Strands Agents с Meta-Tooling

Эта лабораторная работа демонстрирует создание агента на базе **Strands Agents** с возможностью **meta-tooling** (создание инструментов на лету) и его интеграцию с платформой **AI Agents** через протокол A2A.

## Обзор

Strands Agents - это фреймворк от AWS, который поддерживает meta-tooling - способность агента создавать новые инструменты во время выполнения, а также интеграцию с MCP (Model Context Protocol) серверами. В этой лабораторной работе вы:

1. Создадите Strands Agents агента с инструментами для meta-tooling
2. Интегрируете агента с MCP серверами для использования внешних инструментов
3. Научите агента создавать новые инструменты динамически
4. Интегрируете агента с A2A протоколом
5. Развернете агента в платформе AI Agents

## Что такое Meta-Tooling?

Meta-tooling - это способность AI-системы создавать новые инструменты во время выполнения, а не быть ограниченной предопределенным набором возможностей. Агент может:

- Анализировать запрос пользователя
- Создавать новый инструмент для решения задачи
- Загружать инструмент в свою систему
- Использовать созданный инструмент

## Технологии

- **Python 3.12**
- **Strands Agents** (>=0.3.0) - фреймворк с поддержкой meta-tooling
- **MCP** (>=1.0.0) - Model Context Protocol для интеграции с внешними инструментами
- **A2A SDK** (>=0.3.4) - протокол Agent-to-Agent
- **LiteLLM** - унификация доступа к LLM
- **OpenInference** - телеметрия и трейсинг
- **Docker** - контейнеризация

## Структура проекта

```
lab6-strands-agent/
├── src/
│   ├── __init__.py
│   ├── agent.py              # Определение Strands агента с meta-tooling
│   ├── a2a_wrapper.py       # Обертка для A2A протокола
│   ├── agent_task_manager.py # Интеграция с A2A executor
│   └── start_a2a.py         # Точка входа приложения
├── tools/                    # Директория для динамически создаваемых инструментов
├── Dockerfile                # Определение Docker-образа
├── pyproject.toml            # Зависимости проекта
└── README.md                 # Этот файл
```

## Особенности реализации

### 1. Интеграция с MCP (Model Context Protocol)

Агент поддерживает подключение к MCP серверам через `MCPClient` и `streamablehttp_client`:

```python
from strands.tools.mcp.mcp_client import MCPClient
from mcp.client.streamable_http import streamablehttp_client

# Создание транспорта для MCP сервера
transport = streamablehttp_client("http://mcp-server:8000/mcp/")
mcp_client = MCPClient(transport)

# Получение инструментов из MCP сервера
tools = mcp_client.list_tools_sync()
```

Инструменты из MCP серверов автоматически преобразуются в стандартные AgentTools и становятся доступными агенту.

### 2. Инструменты для Meta-Tooling

Агент изначально имеет три ключевых инструмента:

- **load_tool** - загружает новый инструмент в систему агента
- **editor** - создает и редактирует файлы с кодом инструментов
- **shell** - выполняет shell команды для отладки

Эти инструменты можно комбинировать с инструментами из MCP серверов.

### 3. Структура создаваемых инструментов

Каждый новый инструмент должен следовать формату:

```python
from typing import Any
from strands.types.tool_types import ToolUse, ToolResult

TOOL_SPEC = {
    "name": "tool_name",
    "description": "Что делает инструмент",
    "inputSchema": {
        "json": {
            "type": "object",
            "properties": {
                "param_name": {
                    "type": "string",
                    "description": "Описание параметра"
                }
            },
            "required": ["param_name"]
        }
    }
}

def tool_name(tool_use: ToolUse, **kwargs: Any) -> ToolResult:
    tool_use_id = tool_use["toolUseId"]
    param_value = tool_use["input"]["param_name"]
    
    # Логика инструмента
    result = process(param_value)
    
    return {
        "toolUseId": tool_use_id,
        "status": "success",
        "content": [{"text": f"Result: {result}"}]
    }
```

### 4. A2A Обертка

`StrandsA2AWrapper` преобразует интерфейс Strands Agents агента в A2A-совместимый формат:
- Поддержка streaming через `run_stream`
- Управление сессиями и историей диалога
- Обработка ошибок

## Переменные окружения

Агент использует стандартные переменные окружения AI Agents:

| Переменная | Описание |
|------------|----------|
| `LLM_MODEL` | Название модели LLM |
| `LLM_API_BASE` | Базовый URL API для LLM |
| `LLM_API_KEY` | API ключ для доступа к LLM |
| `AGENT_NAME` | Название агента |
| `AGENT_DESCRIPTION` | Описание агента |
| `AGENT_VERSION` | Версия агента |
| `AGENT_SYSTEM_PROMPT` | Системный промпт агента |
| `MCP_URL` | URL MCP-серверов (через запятую, например: `http://server1:8000,http://server2:8000`) |
| `URL_AGENT` | URL агента |
| `PORT` | Порт для запуска сервера |
| `PHOENIX_ENDPOINT` | Endpoint для Phoenix телеметрии |
| `ENABLE_PHOENIX` | Включить телеметрию (true/false) |

## Развертывание

### Шаг 1: Сборка Docker образа

```bash
docker buildx build --platform linux/amd64 -t strands-agent .
```

### Шаг 2: Тегирование образа

```bash
docker tag strands-agent:latest cloudru-labs.cr.cloud.ru/strands-agent-repo:v1.0.0
```

### Шаг 3: Загрузка в Artifact Registry

```bash
docker push cloudru-labs.cr.cloud.ru/strands-agent-repo:v1.0.0
```

### Шаг 4: Создание агента в UI

1. Откройте консоль AI Agents в cloud.ru
2. Создайте нового агента
3. Укажите Docker-образ из Artifact Registry
4. Настройте переменные окружения
5. Сохраните и запустите агента

## Использование

После развертывания агент будет доступен через:
- UI чата в консоли AI Agents
- A2A протокол для интеграции с другими агентами
- REST API через A2A endpoints

## Примеры использования

### Использование MCP инструментов

Если подключен MCP-сервер из lab1 (finance):

```
Пользователь: Рассчитай график аннуитетного кредита на 1 000 000 рублей 
              под 12% годовых на 5 лет

Агент: [Использует инструмент loan_schedule_annuity из MCP сервера]
       [Результат расчета графика платежей]
```

### Создание нового инструмента

```
Пользователь: Создай инструмент, который считает количество символов в тексте

Агент: [Использует editor для создания файла tools/custom_tool_0.py]
       [Использует load_tool для загрузки инструмента]
       Инструмент custom_tool_0 успешно создан и загружен!
```

### Использование созданного инструмента

```
Пользователь: Посчитай символы в тексте "Hello, World!"

Агент: [Использует custom_tool_0]
       Текст "Hello, World!" содержит 13 символов
```

### Комбинирование MCP и созданных инструментов

```
Пользователь: Создай инструмент для анализа финансовых данных, 
              используя данные из MCP сервера

Агент: [Создает инструмент, который использует MCP инструменты внутри]
       [Загружает инструмент]
       Инструмент готов к использованию!
```

## Отличия от других фреймворков

1. **Meta-Tooling**: Уникальная возможность создавать инструменты на лету
2. **MCP интеграция**: Первоклассная поддержка Model Context Protocol для подключения к внешним инструментам
3. **Динамическое расширение**: Агент может расширять свои возможности самостоятельно
4. **Гибкость**: Адаптация к новым задачам без изменения кода агента
5. **Комбинирование**: Возможность комбинировать MCP инструменты с созданными на лету инструментами

## Дополнительные ресурсы

- [Strands Agents Documentation](https://strandsagents.com/0.3.x/documentation/)
- [Meta-Tooling Example](https://strandsagents.com/0.3.x/documentation/docs/examples/python/meta_tooling/)
- [MCP Integration Example](https://strandsagents.com/0.3.x/documentation/docs/examples/python/mcp_calculator/)
- [A2A Protocol](https://github.com/google/a2a)
- [AI Agents Documentation](https://cloud.ru/docs/ai-agents/ug/index)

## Troubleshooting

### Агент не подключается к MCP серверам

Проверьте:
- Правильность URL MCP-серверов в `MCP_URL`
- URL должен быть доступен из контейнера
- MCP сервер должен поддерживать streamable HTTP транспорт
- URL должен заканчиваться на `/mcp/` или `/mcp`

### Агент не создает инструменты

Проверьте:
- Системный промпт должен содержать инструкции по созданию инструментов
- Директория `tools/` должна существовать и быть доступной для записи
- LLM должен иметь достаточно контекста для понимания задачи

### Ошибки при загрузке инструментов

Убедитесь, что:
- Структура инструмента соответствует формату TOOL_SPEC
- Имя функции совпадает с именем в TOOL_SPEC
- Все импорты корректны

### Проблемы с телеметрией

Если Phoenix не работает:
- Проверьте `PHOENIX_ENDPOINT`
- Убедитесь, что `ENABLE_PHOENIX=true`
- Проверьте доступность endpoint из контейнера

## Важные замечания

⚠️ **Файловая система в рантайме**: В AI Agents агенты не должны работать с файловой системой во время выполнения. Все необходимые файлы должны быть упакованы на этапе сборки Docker-образа. Для meta-tooling это ограничение может потребовать специальной обработки или использования in-memory хранилища.


