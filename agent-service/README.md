# agent-service

Сервис агентов для сценария регистрации компании. Реализован `ProfileAgent`, который превращает текстовое описание в структурированный профиль, классифицирует релевантные коды ОКПД2 и сохраняет результат через `db-mcp`.

## Быстрый старт

1. Убедитесь, что запущен MCP сервер `db-mcp` и доступна база PostgreSQL.
2. Заполните переменные окружения:
   - `LLM_API_KEY` – ключ OpenAI-совместимого API.
   - `DB_MCP_URL` – URL HTTP транспорта `db-mcp`, например `http://localhost:8000`.
3. Запустите профильный агент:

```bash
cd agent-service
pip install -e .
export LLM_API_KEY=... 
export DB_MCP_URL=http://localhost:8000
python -m src.start_profile_agent "Мы строительная компания ..."
```

Агент вернет `company_id`, краткий итог и сохранит профиль в БД через MCP инструмент `create_company_profile`.
