# Лабораторная работа 4: SmolAgents Agent для AI Agents

Эта лабораторная работа демонстрирует создание легковесного агента на базе **SmolAgents** (от Hugging Face) и его интеграцию с платформой **AI Agents** через протокол A2A.

## Обзор

SmolAgents - это минималистичный фреймворк от Hugging Face для создания AI-агентов с акцентом на простоту и эффективность. В этой лабораторной работе вы:

1. Создадите SmolAgents агента с поддержкой инструментов
2. Интегрируете агента с MCP-серверами
3. Обернете агента для работы через A2A протокол
4. Развернете агента в платформе AI Agents

## Технологии

- **Python 3.12**
- **SmolAgents** (>=0.1.0) - легковесный фреймворк от Hugging Face
- **A2A SDK** (>=0.3.4) - протокол Agent-to-Agent
- **LiteLLM** - унификация доступа к LLM
- **OpenInference** - телеметрия и трейсинг
- **Docker** - контейнеризация

### ⚠️ Важное примечание для Intel Mac

SmolAgents имеет транзитивную зависимость от `torch`, который **не поддерживает Intel Mac (x86_64)** с macOS 14+. На этой платформе `uv sync` может завершиться ошибкой.

**Решение**: Используйте Docker для разработки и развертывания. Docker-образ использует Linux, где torch полностью поддерживается.

## Структура проекта

```
lab4-smolagents-agent/
├── src/
│   ├── __init__.py
│   ├── agent.py              # Определение SmolAgents агента
│   ├── a2a_wrapper.py        # Обертка для A2A протокола
│   ├── agent_task_manager.py  # Интеграция с A2A executor
│   └── start_a2a.py          # Точка входа приложения
├── Dockerfile                 # Определение Docker-образа
├── pyproject.toml            # Зависимости проекта
└── README.md                  # Этот файл
```

## Особенности реализации

### 1. SmolAgents CodeAgent

Агент создается с использованием `CodeAgent`, который может писать и выполнять Python код:

```python
agent = CodeAgent(
    tools=tools,
    llm=llm_call,
    system_prompt=system_prompt,
    max_iterations=15,
)
```

### 2. Интеграция с MCP

Инструменты из MCP-серверов преобразуются в SmolAgents Tools для использования агентом.

### 3. A2A Обертка

`SmolAgentsA2AWrapper` преобразует интерфейс SmolAgents агента в A2A-совместимый формат:
- Поддержка streaming (если доступен `run_stream`)
- Управление сессиями и историей диалога
- Обработка ошибок

### 4. Легковесность

SmolAgents имеет минимальные зависимости и простой API, что делает его идеальным для быстрого прототипирования.

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
docker buildx build --platform linux/amd64 -t smolagents-agent .
```

### Шаг 2: Тегирование образа

```bash
docker tag smolagents-agent:latest cloudru-labs.cr.cloud.ru/smolagents-agent-repo:v1.0.0
```

### Шаг 3: Загрузка в Artifact Registry

```bash
docker push cloudru-labs.cr.cloud.ru/smolagents-agent-repo:v1.0.0
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

Агент: [Использует инструмент loan_schedule_annuity]
       [Результат расчета графика платежей]
```

### Вычисления через код

SmolAgents может писать и выполнять Python код:

```
Пользователь: Вычисли факториал числа 10

Агент: [Пишет и выполняет Python код]
       Факториал 10 = 3628800
```

## Отличия от других фреймворков

1. **Простота**: Минимальный API и зависимости
2. **Code Agents**: Может писать и выполнять Python код
3. **Эффективность**: Уменьшает количество шагов и вызовов LLM на ~30%
4. **Безопасность**: Поддержка sandboxed execution (E2B)

## Дополнительные ресурсы

- [SmolAgents Documentation](https://smolagents.org/hi/docs/smolagent-docs/)
- [Hugging Face SmolAgents](https://huggingface.co/docs/smolagents)
- [A2A Protocol](https://github.com/google/a2a)
- [AI Agents Documentation](https://cloud.ru/docs/ai-agents/ug/index)

## Troubleshooting

### Агент не использует инструменты

Проверьте:
- Правильность URL MCP-серверов в `MCP_URL`
- Доступность MCP-серверов из контейнера
- Системный промпт должен указывать на использование инструментов

### Ошибки при выполнении кода

SmolAgents может выполнять код. Убедитесь, что:
- Системный промпт разрешает выполнение кода
- Код выполняется безопасно (в sandbox если доступен)

### Проблемы с телеметрией

Если Phoenix не работает:
- Проверьте `PHOENIX_ENDPOINT`
- Убедитесь, что `ENABLE_PHOENIX=true`
- Проверьте доступность endpoint из контейнера


