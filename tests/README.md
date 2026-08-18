# Automated Test Suite

To run tests:

```bash
uv run pytest tests/ -v
```

### Test Coverage:
- `test_database.py`: Tests SQLite table creation, CRUD, and timeframe filtering queries (`all`, `last_week`, `last_month`, `last_year`).
- `test_services.py`: Tests storage manager slugification, file writing, and audio processor pipeline.
- `test_api.py`: Tests FastAPI REST endpoints with `TestClient`.
- `test_mcp_server.py`: Tests FastMCP tool functions (`add_mp3_file`, `list_files`, `query_files`).
