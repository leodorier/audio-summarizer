import os
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

# 1. Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# 2. Avoid local directory shadowing when folder is named 'mcp/'
_original_path = list(sys.path)
_filtered_path = [
    p for p in sys.path
    if not (os.path.isdir(os.path.join(p, "mcp")) and os.path.exists(os.path.join(p, "mcp", "mcp_server.py")))
]
sys.path = _filtered_path
_mcp_module = sys.modules.pop("mcp", None)
try:
    from mcp.server.fastmcp import FastMCP
finally:
    sys.path = _original_path
    if _mcp_module is not None:
        sys.modules["mcp"] = _mcp_module

from app.config import settings
from app.database import (
    init_db, get_audio_records, get_audio_record_by_id
)
from app.services.processor import process_audio_file

# Initialize SQLite schema
init_db()

# 3. Instantiate FastMCP Server
mcp = FastMCP("Audio Summarizer Vault")

@mcp.tool()
def add_mp3_file(file_path: str, title: Optional[str] = None) -> str:
    """
    Ingest, transcribe (STT), and summarize an audio file (MP3, WAV, M4A, OGG, FLAC) from the local filesystem.
    - file_path: Absolute or relative path to the local audio file.
    - title: Optional suggested topic or context title.
    """
    path = Path(file_path).expanduser().resolve()
    if not path.exists():
        return f"❌ Error: Audio file not found at path: `{file_path}`"
    
    try:
        record = process_audio_file(
            source_audio_path=path,
            original_filename=path.name,
            custom_title=title
        )
        
        duration_m = round(record["duration_seconds"] / 60, 1)
        key_pts = "\n".join([f"- {p}" for p in record.get("key_points", [])])
        
        return f"""# ✅ Audio Successfully Processed & Summarized

- **ID**: `#{record['id']}`
- **Title**: **{record['title']}**
- **Original File**: `{record['original_filename']}` ({duration_m} min)
- **Language**: `{record.get('language', 'en').upper()}`
- **Transcript File**: `{record['transcript_file_path']}`
- **Summary File**: `{record['summary_file_path']}`

## 📌 Executive Summary
{record['summary_text']}

## 🔑 Key Points
{key_pts if key_pts else '_None recorded_'}
"""
    except Exception as e:
        return f"❌ Error processing audio file: {str(e)}"

@mcp.tool()
def list_files(limit: int = 50) -> str:
    """
    Retrieve the list of all available processed audio recordings in the database.
    - limit: Maximum number of records to return (default: 50).
    """
    records, total = get_audio_records(timeframe="all", limit=limit)
    if not records:
        return "ℹ️ No audio files have been processed yet in the database."
    
    output = [f"# 🎙️ Processed Audio Files ({len(records)}/{total})\n"]
    output.append("| ID | Title | Date | Duration | Tags |")
    output.append("| :--- | :--- | :--- | :--- | :--- |")
    
    for r in records:
        mins = round(r["duration_seconds"] / 60, 1)
        date_str = r["created_at"][:10] if r["created_at"] else "N/A"
        tags = ", ".join(r.get("topics", [])[:3])
        output.append(f"| `#{r['id']}` | **{r['title']}** | {date_str} | {mins}m | {tags} |")
    
    return "\n".join(output)

@mcp.tool()
def query_files(
    file_id: Optional[int] = None,
    timeframe: str = "all",
    search_query: Optional[str] = None
) -> str:
    """
    Query processed audio recordings.
    - file_id: (Optional) ID of a specific audio record to view full transcript and summary.
    - timeframe: Filter range: 'last_week', 'last_month', 'last_year', or 'all' (default: 'all').
    - search_query: (Optional) Search keyword within title, transcript, summary, or topics.
    """
    if file_id is not None:
        record = get_audio_record_by_id(file_id)
        if not record:
            return f"❌ Record `#{file_id}` not found."
        
        return f"""# 📋 Audio Record `#{record['id']}`: {record['title']}

- **Date**: {record['created_at']}
- **Original Audio**: `{record['original_filename']}` ({round(record['duration_seconds']/60, 1)}m)
- **Language**: `{record.get('language', 'en').upper()}`
- **Topics**: {', '.join(record.get('topics', []))}
- **Summary File**: `{record['summary_file_path']}`
- **Transcript File**: `{record['transcript_file_path']}`

---

## 📌 Executive Summary
{record['summary_text']}

---

## 🔑 Key Points
{chr(10).join(['- ' + p for p in record.get('key_points', [])])}

---

## ⚡ Action Items
{chr(10).join(['- [ ] ' + a for a in record.get('action_items', [])]) or '_No action items_'}

---

## 🎙️ Full Verbatim Transcript
```text
{record['raw_transcript']}
```
"""

    records, total = get_audio_records(timeframe=timeframe, search_query=search_query, limit=20)
    if not records:
        return f"ℹ️ No audio files found matching timeframe='{timeframe}' and query='{search_query or ''}'."
    
    results = [f"# 🔍 Query Results ({len(records)} found for timeframe='{timeframe}')\n"]
    for r in records:
        results.append(f"### `#{r['id']}`: {r['title']}")
        results.append(f"- **Date**: {r['created_at']} | **Duration**: {round(r['duration_seconds']/60, 1)}m")
        results.append(f"- **Summary**: {r['summary_text'][:250]}...")
        if r.get("key_points"):
            results.append(f"- **Top Insight**: {r['key_points'][0]}")
        results.append("")
    
    return "\n".join(results)

if __name__ == "__main__":
    transport = os.environ.get("MCP_TRANSPORT", "stdio").lower()
    if transport == "sse":
        port = int(os.environ.get("MCP_PORT", 3000))
        mcp.run(transport="sse", port=port)
    else:
        mcp.run(transport="stdio")
