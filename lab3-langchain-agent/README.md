# Лабораторная работа 3: LangChain Agent для AI Agents

Эта лабораторная работа демонстрирует создание агента на базе **LangChain** и его интеграцию с платформой **AI Agents** через протокол A2A.

## Обзор

LangChain - один из самых популярных фреймворков для создания AI-агентов. В этой лабораторной работе вы:

1. Создадите LangChain агента с поддержкой инструментов
2. Интегрируете агента с MCP-серверами
3. Обернете агента для работы через A2A протокол
4. Развернете агента в платформе AI Agents

## Технологии

- **Python 3.12**
- **LangChain** (>=0.3.0) - фреймворк для создания агентов
- **LangChain OpenAI** - интеграция с OpenAI-совместимыми моделями
- **A2A SDK** (>=0.3.4) - протокол Agent-to-Agent
- **LiteLLM** - унификация доступа к LLM
- **OpenInference** - телеметрия и трейсинг
- **Docker** - контейнеризация

## Структура проекта

```
lab3-langchain-agent/
├── src/
│   ├── __init__.py
│   ├── agent.py              # Определение LangChain агента
│   ├── a2a_wrapper.py        # Обертка для A2A протокола
│   ├── agent_task_manager.py  # Интеграция с A2A executor
│   └── start_a2a.py          # Точка входа приложения
├── Dockerfile                 # Определение Docker-образа
├── pyproject.toml            # Зависимости проекта
└── README.md                  # Этот файл
```

## Особенности реализации

### 1. LangChain Agent

Агент создается с использованием `AgentExecutor` и `create_openai_tools_agent`:

```python
agent = create_openai_tools_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
```

### 2. Интеграция с MCP

Инструменты из MCP-серверов преобразуются в LangChain Tools для использования агентом.

### 3. A2A Обертка

`LangChainA2AWrapper` преобразует интерфейс LangChain агента в A2A-совместимый формат:
- Поддержка streaming через `astream`
- Управление сессиями и историей диалога
- Обработка ошибок

### 4. Телеметрия

Интеграция с Phoenix/OpenInference для отслеживания работы агента.

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
| `MCP_URL` | URL MCP-серверов (через запятую) |
| `URL_AGENT` | URL агента |
| `PORT` | Порт для запуска сервера |
| `PHOENIX_ENDPOINT` | Endpoint для Phoenix телеметрии |
| `ENABLE_PHOENIX` | Включить телеметрию (true/false) |

## Развертывание

### Шаг 1: Сборка Docker образа

```bash
docker buildx build --platform linux/amd64 -t langchain-agent .
```

### Шаг 2: Тегирование образа

```bash
docker tag langchain-agent:latest cloudru-labs.cr.cloud.ru/langchain-agent-repo:v1.0.0
```

### Шаг 3: Загрузка в Artifact Registry

```bash
docker push cloudru-labs.cr.cloud.ru/langchain-agent-repo:v1.0.0
```

### Шаг 4: Создание агента в UI

1. Откройте консоль AI Agents в cloud.ru
2. Создайте нового агента
3. Укажите Docker-образ из Artifact Registry
4. Настройте переменные окружения
5. Выберите MCP-серверы (опционально)
6. Сохраните и запустите агента

## Использование

После развертывания агент будет доступен через:
- UI чата в консоли AI Agents
- A2A протокол для интеграции с другими агентами
- REST API через A2A endpoints

## Примеры использования

### Финансовые расчеты

Если подключен MCP-сервер из lab1:

```
Пользователь: Рассчитай график аннуитетного кредита на 1 000 000 рублей 
              под 12% годовых на 5 лет

Агент: Использую инструмент: loan_schedule_annuity
       [Результат расчета графика платежей]
```

### Общие вопросы

```
Пользователь: Привет! Расскажи о себе

Агент: Привет! Я LangChain агент, созданный для работы в платформе AI Agents. 
       Я могу использовать различные инструменты для решения задач...
```

## Отличия от Google ADK (lab2)

1. **Фреймворк**: LangChain вместо Google ADK
2. **Инструменты**: Преобразование MCP инструментов в LangChain Tools
3. **Streaming**: Использование `astream` вместо `run_async`
4. **История**: Простое хранение в памяти вместо SessionService

## Дополнительные ресурсы

- [Документация LangChain](https://python.langchain.com/)
- [LangChain Agents](https://python.langchain.com/docs/modules/agents/)
- [A2A Protocol](https://github.com/google/a2a)
- [AI Agents Documentation](https://cloud.ru/docs/ai-agents/ug/index)

## Troubleshooting

### Агент не использует инструменты

Проверьте:
- Правильность URL MCP-серверов в `MCP_URL`
- Доступность MCP-серверов из контейнера
- Системный промпт должен указывать на использование инструментов

### Ошибки при streaming

Убедитесь, что:
- LLM поддерживает streaming
- `LLM_API_BASE` указывает на правильный endpoint
- API ключ валиден

### Проблемы с телеметрией

Если Phoenix не работает:
- Проверьте `PHOENIX_ENDPOINT`
- Убедитесь, что `ENABLE_PHOENIX=true`
- Проверьте доступность endpoint из контейнера


