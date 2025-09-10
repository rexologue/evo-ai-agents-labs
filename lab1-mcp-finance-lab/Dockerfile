FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml pyproject.toml

RUN pip install poetry \
    && poetry config virtualenvs.in-project true \
    && poetry install --no-interaction --no-ansi

COPY src src

ENV PATH="/app/.venv/bin:$PATH"

CMD ["python", "src/main.py"]
