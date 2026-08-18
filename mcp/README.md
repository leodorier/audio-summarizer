# 🔌 Audio Summarizer MCP Server

Model Context Protocol (MCP) server providing AI coding assistants direct tool access to transcribe, summarize, and query speech audio recordings.

## Available Tools

1. **`add_mp3_file(file_path: str, title: Optional[str] = None)`**:
   Upload and process a local audio file (.mp3, .wav, .m4a, .ogg, .flac). Performs Gemini STT transcription, executive summarization, and stores transcript + summary files.
2. **`list_files(limit: int = 50)`**:
   Retrieve the table of all processed audio files in the database.
3. **`query_files(file_id: Optional[int] = None, timeframe: str = "all", search_query: Optional[str] = None)`**:
   Retrieve full transcripts and summaries for a specific audio ID, or search records across timeframes (`last_week`, `last_month`, `last_year`, `all`).

## Configuration

Add to `~/.gemini/config/mcp_config.json`:

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
