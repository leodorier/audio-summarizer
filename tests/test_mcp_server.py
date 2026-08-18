import pytest
from unittest.mock import patch
from mcp.mcp_server import list_files, query_files, add_mp3_file
from app.database import add_audio_record
from app.schemas import AudioRecordCreate

def test_mcp_tools(temp_storage, mock_extraction, sample_audio_file):
    # 1. Test empty list
    empty_res = list_files()
    assert "No audio files have been processed" in empty_res

    # 2. Ingest via add_mp3_file tool
    with patch("app.services.processor.transcribe_and_summarize_audio", return_value=mock_extraction):
        add_res = add_mp3_file(str(sample_audio_file), title="MCP Ingestion Test")
        assert "Audio Successfully Processed" in add_res
        assert "AI Architecture Deep Dive" in add_res

    # 3. List files after ingestion
    list_res = list_files()
    assert "Processed Audio Files" in list_res
    assert "AI Architecture Deep Dive" in list_res

    # 4. Query files by timeframe
    q_all = query_files(timeframe="all")
    assert "AI Architecture Deep Dive" in q_all

    # 5. Query specific file ID
    q_id = query_files(file_id=1)
    assert "Full Verbatim Transcript" in q_id
    assert "Executive Summary" in q_id
