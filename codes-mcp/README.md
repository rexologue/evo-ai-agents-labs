## Запуск из контейнера
```bash
docker buildx build --platform linux/amd64 -t codes-mcp -f Dockerfile ..
docker run --rm --network host --env-file .env codes-mcp
```

## 📖 Инструментs
- `get_okdp2_codes()` — выдает таблицу кодов и соответствующих им наименований по ОКПД2.
- `get_region_codes()` — выдает таблицу кодов регионов.


