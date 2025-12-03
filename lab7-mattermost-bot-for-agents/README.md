# Mattermost Bot для A2A агента

Бот для Mattermost, интегрированный с A2A агентом, с поддержкой streaming ответов, команд и полной OpenInference телеметрией.

---

## Важные моменты

### 1. Назначение бота
Бот позволяет интегрировать A2A агента в Mattermost, обеспечивая:
- Ответы на упоминания бота (@bot_name)
- Обработку прямых сообщений (DM)
- Поддержку команд (например, `/a2a help`, `/a2a status`)
- Streaming ответы от A2A агента
- Полную телеметрию через OpenInference и OpenTelemetry

### 2. Требования
- Python 3.8 или выше
- [uv](https://github.com/astral-sh/uv) - быстрый менеджер пакетов Python
- Доступ к Mattermost серверу
- Доступ к A2A агенту
- OTLP collector для телеметрии (опционально)

---

## Пошаговый гайд

### Шаг 1. Подготовка окружения

#### 1.1 Установка uv

```bash
# На Linux/Mac:
curl -LsSf https://astral.sh/uv/install.sh | sh

# На Windows:
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Или через pip:
pip install uv
```

#### 1.2 Клонирование и подготовка проекта

```bash
# Перейдите в директорию проекта
cd mattermost-bot-for-a2a
```

#### 1.3 Установка зависимостей

```bash
# Установка через uv pip
uv pip install -r requirements.txt
```

**Примечание:** Файл `requirements.txt` используется для установки зависимостей. `pyproject.toml` используется для описания проекта.

---

### Шаг 2. Настройка переменных окружения

#### 2.1 Создание .env файла

Создайте файл `.env` на основе примера:

```bash
cp .env.example .env
```

#### 2.2 Получение токена Mattermost

1. Войдите в Mattermost как администратор
2. Перейдите в **System Console** → **Integrations** → **Bot Accounts**
3. Создайте нового бота или используйте существующего
4. Скопируйте **Access Token** бота
5. Вставьте токен в переменную `MATTERMOST_TOKEN` в `.env` файле

**Альтернативный способ через API:**

```bash
# Получите Personal Access Token для создания бота
curl -X POST https://your-mattermost-server.com/api/v4/users \
  -H "Authorization: Bearer YOUR_PERSONAL_ACCESS_TOKEN" \
  -d '{
    "email": "bot@example.com",
    "username": "a2a-bot",
    "password": "secure_password",
    "nickname": "A2A Bot"
  }'

# Затем получите токен для бота
curl -X POST https://your-mattermost-server.com/api/v4/users/login \
  -d '{"login_id": "a2a-bot", "password": "secure_password"}'
```

#### 2.3 Настройка A2A агента

1. Убедитесь, что у вас есть доступ к A2A агенту
2. Получите базовый URL агента (например, `https://7d0939e3-38e1-4f8d-a0a2-773629701cde-agent.ai-agent.inference.cloud.ru`)
3. Получите токен доступа к агенту
4. Заполните `A2A_BASE_URL` и `A2A_TOKEN` в `.env` файле

#### 2.4 Настройка телеметрии (опционально)

Если у вас есть OTLP collector:

1. Укажите endpoint в `OTEL_EXPORTER_OTLP_ENDPOINT`
2. По умолчанию используется HTTP endpoint (`http://localhost:4318`)
3. Для gRPC используйте формат `http://localhost:4317`

Если телеметрия не нужна, можно указать фиктивный endpoint - бот продолжит работать, но телеметрия не будет отправляться.

#### 2.5 Пример .env файла

```bash
# Mattermost Configuration
MATTERMOST_URL=https://your-mattermost-server.com
MATTERMOST_TOKEN=your_mattermost_bot_token
MATTERMOST_BOT_USERNAME=a2a-bot

# A2A Agent Configuration
A2A_BASE_URL=https://your-agent-id-agent.ai-agent.inference.cloud.ru
A2A_TOKEN=your_a2a_agent_token

# OpenTelemetry/OpenInference Configuration
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
OTEL_SERVICE_NAME=mattermost-a2a-bot

# Logging
LOG_LEVEL=INFO
```

---

### Шаг 3. Запуск бота

#### 3.1 Базовый запуск

```bash
# Через uv (рекомендуется)
uv run python bot.py

# Или активируйте виртуальное окружение
source .venv/bin/activate  # Linux/Mac
python bot.py
```

#### 3.2 Запуск в Docker

Создайте `Dockerfile`:

```dockerfile
FROM python:3.11-slim

# Установка uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Копируем файлы проекта
COPY requirements.txt ./
COPY . .

# Устанавливаем зависимости через uv
RUN uv pip install --system -r requirements.txt

# Запуск бота
CMD ["uv", "run", "python", "bot.py"]
```

Создайте `docker-compose.yml`:

```yaml
version: '3.8'

services:
  mattermost-bot:
    build: .
    container_name: mattermost-a2a-bot
    restart: unless-stopped
    env_file:
      - .env
    volumes:
      - ./logs:/app/logs
```

Запуск:

```bash
docker-compose up -d
docker-compose logs -f
```

#### 3.3 Запуск как systemd service (Linux)

Создайте файл `/etc/systemd/system/mattermost-a2a-bot.service`:

```ini
[Unit]
Description=Mattermost A2A Bot
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/mattermost-bot-for-a2a
Environment="PATH=/usr/local/bin:/usr/bin:/bin"
ExecStart=/usr/local/bin/uv run python bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Затем:

```bash
# Перезагрузите systemd
sudo systemctl daemon-reload

# Включите сервис
sudo systemctl enable mattermost-a2a-bot

# Запустите сервис
sudo systemctl start mattermost-a2a-bot

# Проверьте статус
sudo systemctl status mattermost-a2a-bot

# Просмотр логов
sudo journalctl -u mattermost-a2a-bot -f
```

---

### Шаг 4. Проверка работы

1. **Проверьте логи** - бот должен вывести сообщения об успешной инициализации:
   ```
   INFO - Телеметрия настроена
   INFO - A2A клиент инициализирован
   INFO - Подключение к Mattermost установлено
   INFO - WebSocket соединение установлено, бот готов к работе
   ```

2. **Проверьте команду status**:
   - В Mattermost отправьте: `/a2a status`
   - Бот должен ответить статусом подключения

3. **Проверьте команду help**:
   - В Mattermost отправьте: `/a2a help`
   - Бот должен показать справку с доступными skills агента

4. **Проверьте упоминание**:
   - Упомяните бота в канале: `@bot_name Привет!`
   - Бот должен ответить через A2A агента

---

### Шаг 5. Использование

#### Упоминания бота
В любом канале упомяните бота:
```
@bot_name Какой курс доллара?
```

#### Прямые сообщения
Отправьте боту прямое сообщение в Mattermost

#### Команды
- `/a2a help` - показать справку с доступными skills агента
- `/a2a status` - проверить статус подключения к A2A агенту
- Остальные команды передаются напрямую в A2A агент

---

## Конфигурация

Все настройки выполняются через переменные окружения:

| Переменная | Описание | Обязательно |
|-----------|----------|-------------|
| `MATTERMOST_URL` | URL вашего Mattermost сервера | Да |
| `MATTERMOST_TOKEN` | Токен бота | Да |
| `MATTERMOST_BOT_USERNAME` | Имя пользователя бота (опционально, определяется автоматически) | Нет |
| `A2A_BASE_URL` | Базовый URL A2A агента | Да |
| `A2A_TOKEN` | Токен для доступа к A2A агенту | Да |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | Endpoint для экспорта телеметрии | Да |
| `OTEL_SERVICE_NAME` | Имя сервиса для телеметрии (по умолчанию: mattermost-a2a-bot) | Нет |
| `LOG_LEVEL` | Уровень логирования: DEBUG, INFO, WARNING, ERROR (по умолчанию: INFO) | Нет |

---

## Телеметрия

Бот автоматически отправляет телеметрию через OpenInference:
- Traces для всех запросов
- Spans с метаданными (message_id, channel_id, user_id, response_time)
- Метрики производительности
- Информация о skills агента

Убедитесь, что `OTEL_EXPORTER_OTLP_ENDPOINT` указывает на ваш OTLP collector.

---

## Устранение неполадок

### Бот не отвечает на сообщения

1. Проверьте логи на наличие ошибок
2. Убедитесь, что токен Mattermost корректен
3. Проверьте, что бот добавлен в канал или имеет права на чтение сообщений
4. Убедитесь, что WebSocket соединение установлено (проверьте логи)

### Ошибка подключения к A2A агенту

1. Проверьте `A2A_BASE_URL` и `A2A_TOKEN`
2. Убедитесь, что агент доступен по указанному URL
3. Проверьте сетевые настройки и firewall
4. Попробуйте выполнить тестовый запрос к агенту вручную

### Ошибки телеметрии

1. Если телеметрия не критична, можно указать фиктивный endpoint
2. Проверьте доступность OTLP collector
3. Убедитесь, что endpoint указан правильно (HTTP: порт 4318, gRPC: порт 4317)

### Бот не показывает skills в help

1. Убедитесь, что agent_card содержит информацию о skills
2. Проверьте структуру ответа от A2A агента
3. Посмотрите логи на предупреждения о получении skills

---

## Структура проекта

```
mattermost-bot-for-a2a/
├── bot.py                 # Основной файл бота
├── a2a_client.py          # Обертка для A2A клиента с телеметрией
├── mattermost_handler.py  # Обработчики Mattermost событий
├── commands.py            # Обработка команд бота
├── telemetry.py           # Настройка OpenInference телеметрии
├── config.py              # Загрузка конфигурации из env
├── pyproject.toml         # Конфигурация проекта и зависимости (uv)
├── uv.lock                # Lock файл зависимостей (uv, создается автоматически)
├── requirements.txt       # Зависимости (для обратной совместимости)
├── .env.example           # Пример конфигурации
└── README.md              # Документация
```

---

## Разработка

### Настройка окружения для разработки

```bash
# Установка зависимостей через uv
uv pip install -r requirements.txt

# Добавление dev зависимостей (если нужно)
uv add --dev black flake8 mypy pytest

# Активация виртуального окружения (если нужно работать напрямую)
source .venv/bin/activate  # Linux/Mac
# или
.venv\Scripts\activate  # Windows
```

**Примечание:** uv автоматически создает `.venv` в корне проекта.

### Запуск в режиме разработки

```bash
# С уровнем логирования DEBUG через uv
LOG_LEVEL=DEBUG uv run python bot.py

# Или активируйте venv и запускайте напрямую
source .venv/bin/activate
LOG_LEVEL=DEBUG python bot.py
```

---

## Резюме

* Бот интегрирует A2A агента в Mattermost
* Поддерживает streaming ответы и команды
* Полная телеметрия через OpenInference
* Основной процесс: **настроить → запустить → использовать**
