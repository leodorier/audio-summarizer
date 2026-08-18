import pytest
import tempfile
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock
from app.config import settings
from app.database import init_db
from app.schemas import GeminiAudioExtraction

@pytest.fixture
def temp_storage(tmp_path, monkeypatch):
    """Provides isolated temp directories for tests."""
    temp_dir = tmp_path / "storage"
    uploads = temp_dir / "uploads"
    transcripts = temp_dir / "transcripts"
    summaries = temp_dir / "summaries"
    db_path = temp_dir / "test_audio.db"
    
    for d in [temp_dir, uploads, transcripts, summaries]:
        d.mkdir(parents=True, exist_ok=True)
        
    monkeypatch.setattr(settings, "STORAGE_DIR", temp_dir)
    monkeypatch.setattr(settings, "UPLOADS_DIR", uploads)
    monkeypatch.setattr(settings, "TRANSCRIPTS_DIR", transcripts)
    monkeypatch.setattr(settings, "SUMMARIES_DIR", summaries)
    monkeypatch.setattr(settings, "DB_PATH", db_path)
    
    init_db(db_path)
    return {
        "dir": temp_dir,
        "uploads": uploads,
        "transcripts": transcripts,
        "summaries": summaries,
        "db": db_path
    }

@pytest.fixture
def mock_extraction():
    return GeminiAudioExtraction(
        title="AI Architecture Deep Dive",
        language="en",
        transcript="In this session we discuss modular agents, MCP servers, and vector retrieval systems for production environments.",
        executive_summary="The lecture details how modern AI agents leverage standard protocols like MCP to access tools and file systems securely.",
        key_points=[
            "MCP standardizes AI tool interfaces",
            "SQLite WAL mode provides robust single-node storage",
            "Gemini 2.5 Flash handles multimodal audio ingestion natively"
        ],
        action_items=[
            "Deploy reverse proxy on VPS",
            "Register tool in MCP config"
        ],
        topics=["ai-agents", "mcp", "system-architecture", "gemini"]
    )

@pytest.fixture
def sample_audio_file(tmp_path):
    f = tmp_path / "sample_speech.mp3"
    # Create minimal dummy audio file bytes
    f.write_bytes(b"\xFF\xFB\x90\x44\x00\x00\x00\x00" * 100)
    return f
