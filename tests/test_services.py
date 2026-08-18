import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from app.services.storage_manager import (
    slugify, save_uploaded_audio, write_transcript_files,
    write_summary_file, delete_stored_files
)
from app.services.processor import process_audio_file
from app.schemas import GeminiAudioExtraction

def test_slugify():
    assert slugify("Weekly Engineering Sync! #123") == "weekly-engineering-sync-123"
    assert slugify("Café & Croissant 2026") == "café-croissant-2026"
    assert slugify("   ") == "audio"

def test_storage_manager_files(temp_storage, mock_extraction, sample_audio_file):
    # 1. Save uploaded audio
    saved_path, ext = save_uploaded_audio(sample_audio_file, "meeting.mp3")
    assert saved_path.exists()
    assert ext == "mp3"
    
    # 2. Write transcript files
    txt_p, md_p = write_transcript_files(
        base_name="meeting_test",
        title=mock_extraction.title,
        transcript=mock_extraction.transcript,
        original_audio_name=saved_path.name,
        duration_seconds=95.0
    )
    assert txt_p.exists()
    assert md_p.exists()
    assert mock_extraction.transcript in txt_p.read_text(encoding="utf-8")
    assert "# 🎙️ Full Transcript" in md_p.read_text(encoding="utf-8")
    
    # 3. Write summary file
    sum_p = write_summary_file(
        base_name="meeting_test",
        extraction=mock_extraction,
        original_audio_name=saved_path.name,
        duration_seconds=95.0
    )
    assert sum_p.exists()
    assert "## 📌 Executive Summary" in sum_p.read_text(encoding="utf-8")
    assert "MCP standardizes AI tool interfaces" in sum_p.read_text(encoding="utf-8")
    
    # 4. Cleanup
    delete_stored_files(str(saved_path), str(md_p), str(sum_p))
    assert not saved_path.exists()
    assert not md_p.exists()
    assert not sum_p.exists()
    assert not txt_p.exists()

def test_processor_pipeline(temp_storage, mock_extraction, sample_audio_file):
    with patch("app.services.processor.transcribe_and_summarize_audio", return_value=mock_extraction):
        record = process_audio_file(
            source_audio_path=sample_audio_file,
            original_filename="sample_speech.mp3",
            custom_title="Custom Session Title",
            db_path=temp_storage["db"]
        )
        
        assert record is not None
        assert record["title"] == "AI Architecture Deep Dive"
        assert record["status"] == "completed"
        assert Path(record["transcript_file_path"]).exists()
        assert Path(record["summary_file_path"]).exists()
        assert len(record["key_points"]) == 3
