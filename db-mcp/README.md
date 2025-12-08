# db-mcp

MCP сервер для работы с профилями компаний и результатами поиска закупок. Сервер предоставляет инструменты для создания и получения профилей компаний в PostgreSQL.

## Запуск локально

```bash
cd db-mcp
pip install -e .
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=agents
export DB_USER=postgres
export DB_PASSWORD=postgres
export PORT=8000
python -m src.main
```

Сервер автоматически создаст таблицу `companies` при первом запуске.

## Доступные инструменты
- `create_company_profile(profile: CompanyProfileBase) -> CompanyProfileDB`
- `get_company_profile(company_id: str) -> CompanyProfileDB`
- `list_company_profiles(query: Optional[str], limit: int = 20, offset: int = 0) -> list[CompanyProfileDB]`
