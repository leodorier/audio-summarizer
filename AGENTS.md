# audio-summarizer — agent rules

Stack: Python (FastAPI) + SQLite (WAL) + google-genai + FastMCP
Entry: `app/main.py`, `app/static/app.js`
Test: `pytest` · Run: uvicorn (see `Dockerfile`) · MCP: `mcp/mcp_server.py`

Architecture:
- `app/services/` (STT + Gemini summarization, `auth_service`), `app/static/app.js`,
  `mcp/` (`add_mp3_file`, `list_files`, `query_files`).

Rules:
- SQLite `journal_mode=WAL`; SSO via `leolab-auth`.
- Check both `better-auth.session_token` and `__Secure-better-auth.session_token`.
- Keep the `mcp/` local-directory shadowing fix in `mcp/mcp_server.py`.

Do not touch: `storage/{uploads,transcripts,summaries}`, `*.db*`, `.env`.
Memory: `MEMORY.md` (current release only).
