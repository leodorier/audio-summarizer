# 🎙️ Audio Summarizer (`audiosum.leolab.app`)

An automated Speech-to-Text (STT) transcription and executive intelligence summarization engine. Transforms speech audio files (MP3, WAV, M4A, OGG, FLAC) into high-accuracy verbatim transcripts, dense structured notes, key conceptual takeaways, and action items using **Google Gemini 2.5 / 3.7 Flash** multimodal audio understanding.

---

## 🚀 Key Features

* **Multimodal Audio Intelligence**: Direct audio ingestion via Google Gemini File API (`google-genai` SDK) to produce full verbatim Speech-to-Text transcripts and structured summaries in a single pass.
* **Dual Output File Generation**:
  - `storage/transcripts/<id>_<slug>_transcript.md` (and `.txt`): Full verbatim spoken text with speaker/metadata frontmatter.
  - `storage/summaries/<id>_<slug>_summary.md`: Clean Markdown executive summary, categorized bullet points, action items, and topic tags.
* **SQLite Storage Layer**: Fast, zero-config embedded SQLite database with WAL mode (`storage/audio_summarizer.db`) storing metadata, timestamps, audio durations, and JSON tags.
* **Interactive SPA Web Dashboard**:
  - Drag-and-drop audio uploading with live progress feedback.
  - HTML5 audio playback bar with seeking and volume controls.
  - Filterable by timeframe (`All Time`, `Last Week`, `Last Month`, `Last Year`) and instant keyword search.
  - Side-by-side / tabbed inspection for executive summaries and full transcripts.
  - One-click copy to clipboard and file downloads (.txt / .md).
* **Model Context Protocol (MCP) Server**: Exposes 3 standard FastMCP tools for AI coding assistants (Antigravity CLI, Claude Desktop, Gemini) to ingest local MP3s, list recordings, and filter query history.
* **Containerized & Production Ready**: Deployed on VPS with Docker Compose, attached to the `reverse-proxy` network, and served over HTTPS at `audiosum.leolab.app` via Caddy.

---

## 🏗️ Architecture

```text
audio-summarizer/
├── app/                  # FastAPI backend, services, SQLite DB & web UI
│   ├── services/         # Storage manager, Gemini audio extractor, Processor pipeline
│   └── static/           # Single Page Application (HTML5, Tailwind CSS, JS)
├── mcp/                  # FastMCP Server (add_mp3_file, list_files, query_files)
├── storage/              # Persistent SQLite DB, uploaded audio, transcripts, summaries
├── tests/                # Automated pytest suite (DB, Services, API, MCP)
├── Dockerfile            # Multi-stage Python 3.12 + ffmpeg container
├── docker-compose.yml    # Attached to reverse-proxy network
└── docs/                 # Architecture specifications & notes
```

---

## ⚡ Quick Start

### 1. Local Setup with `uv`

```bash
# Clone repository
git clone git@github.com:leodorier/audio-summarizer.git
cd audio-summarizer

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Fill in your GEMINI_API_KEY in .env

# Run development server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Open [http://localhost:8000](http://localhost:8000) in your browser.

---

## 🔌 Model Context Protocol (MCP) Server

To run the local MCP server for AI coding assistants:

```bash
python mcp/mcp_server.py
```

### Configure in Antigravity CLI / Assistant (`~/.gemini/config/mcp_config.json`):

```json
{
  "mcpServers": {
    "audio-summarizer": {
      "command": "python",
      "args": ["/home/leo/projects/audio-summarizer/mcp/mcp_server.py"]
    }
  }
}
```

### Available MCP Tools:
1. **`add_mp3_file(file_path, title)`**: Ingest and transcribe/summarize a local audio file.
2. **`list_files(limit)`**: List all processed audio recordings in database.
3. **`query_files(file_id, timeframe, search_query)`**: Query full transcripts or filter by timeframe (`last_week`, `last_month`, `last_year`, `all`).

---

## 🧪 Testing

```bash
# Run full automated test suite
source .venv/bin/activate
uv run pytest tests/ -v
```

---

## 🐳 Docker Deployment

```bash
# Build and run with Docker Compose
docker compose up -d --build
```
