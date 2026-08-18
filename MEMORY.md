# Project Memory: `audio-summarizer`

## 1. System Overview & Architectural Decisions

### Context
`audio-summarizer` is a microservice and web portal designed to ingest speech audio files, transcribe them to text (STT), distill structured executive summaries via Google Gemini, and persist the outputs into separate Markdown/text files alongside SQLite metadata.

### Architecture Decisions
- **Centralized Better Auth Proxy**:
  - *Decision*: Secure the web portal and API routes using the centralized Better Auth gateway (`second-brain-brain-api:8787` on Docker network, fallback: `https://api-brain.leolab.app`).
  - *Rationale*: Unified single sign-on across the whole suite (`ai-tool`, `instagram-extractor`, and `audio-summarizer`), with TTL session caching (60s) to minimize cross-container latency.
- **Gemini Multimodal Audio vs Local Whisper**:
  - *Decision*: Leverage Google Gemini File API (`google-genai` SDK, `gemini-2.5-flash` / `gemini-3.7-flash`) for combined verbatim STT and structured knowledge distillation.
  - *Rationale*: Zero heavy local GPU overhead, handles long-form audio files in standard audio containers, produces both verbatim speech transcript and structured JSON summaries in a single unified pass.
- **SQLite Single-Node Storage with WAL Mode**:
  - *Decision*: Use SQLite with `journal_mode=WAL` and `synchronous=NORMAL` in `storage/audio_summarizer.db`.
  - *Rationale*: Self-contained, zero network latency, file-backed persistence, matches `instagram-extractor` pattern.
- **Model Context Protocol (MCP)**:
  - *Decision*: FastMCP stdio/SSE dual transport with `add_mp3_file`, `list_files`, and `query_files` tools.
  - *Rationale*: Allows Antigravity, Claude, and Gemini assistants to ingest and reference audio meeting notes directly during chat sessions.
- **Production Host**:
  - *Decision*: Hosted strictly at `audiosum.leolab.app` via Caddy reverse proxy on the VPS `reverse-proxy` Docker network.

---

## 2. Pitfalls & Insights

### Pitfall 1: Local Directory Shadowing with `mcp/` Folder
- **Symptom**: `ImportError: cannot import name 'FastMCP' from partially initialized module 'mcp'` when running `python mcp/mcp_server.py`.
- **Cause**: Python resolves the current directory `mcp/` before the installed pip `mcp` package in `sys.path`.
- **Fix**: Implemented path filtering and temporary `sys.modules.pop("mcp")` in `mcp/mcp_server.py` before importing `mcp.server.fastmcp`.

### Pitfall 2: Better Auth Session Token Cookie Names
- **Symptom**: Session cookies not recognized in production HTTPS vs local development.
- **Cause**: In production over HTTPS, Better Auth uses `__Secure-better-auth.session_token`, whereas non-TLS uses `better-auth.session_token`.
- **Fix**: In `verify_session`, check both `better-auth.session_token` and `__Secure-better-auth.session_token` as well as Bearer headers.

---

## 3. Critical Configuration & Handles

- **Domain**: `https://audiosum.leolab.app`
- **Container Name**: `audio-summarizer`
- **Internal Port**: `8000`
- **Better Auth Endpoint**: `http://second-brain-brain-api:8787` (Fallback: `https://api-brain.leolab.app`)
- **Storage Directory**: `/home/leo/projects/audio-summarizer/storage`
  - `uploads/`: Saved audio files
  - `transcripts/`: Full `.txt` and `.md` transcripts
  - `summaries/`: Structured Markdown summaries
  - `audio_summarizer.db`: SQLite database
- **MCP Config Identifier**: `"audio-summarizer"`
