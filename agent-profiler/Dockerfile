# Используем официальный образ Python 3.13 slim для минимального размера
FROM python:3.13-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Устанавливаем системные зависимости и uv в одном слое для оптимизации
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir uv

# Копируем файлы конфигурации uv сначала для лучшего кеширования Docker слоев
COPY agent-profiler/pyproject.toml ./

# Создаем виртуальное окружение и устанавливаем зависимости
# Используем тот же подход, что и локально
RUN uv sync --no-editable

# Копируем исходный код приложения
COPY agent-profiler/src/ ./src/
COPY models.py ./src/models.py

# Создаем непривилегированного пользователя для безопасности
RUN useradd --create-home --shell /bin/bash --uid 1000 mcp && \
    chown -R mcp:mcp /app

# Переключаемся на непривилегированного пользователя
USER mcp

# Открываем порт для A2A сервера агента (AGENT_PORT по умолчанию 8001)
EXPOSE 8001

# Устанавливаем переменные окружения для оптимальной работы Python
ENV PYTHONPATH=/app \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    UV_SYSTEM_PYTHON=1

# Команда запуска сервера - точно так же, как локально
CMD ["uv", "run", "python", "src/start_a2a.py"]
