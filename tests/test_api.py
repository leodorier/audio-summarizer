import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings

@pytest.fixture
def client(temp_storage):
    return TestClient(app)

def test_health_check(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["app"] == "Audio Summarizer"

def test_upload_and_query_flow(client, sample_audio_file, mock_extraction):
    # 1. Upload audio file with mocked Gemini service
    with patch("app.services.processor.transcribe_and_summarize_audio", return_value=mock_extraction):
        with open(sample_audio_file, "rb") as f:
            res = client.post(
                "/api/upload",
                files={"file": ("speech.mp3", f, "audio/mp3")},
                data={"title": "Test AI Talk"}
            )
        assert res.status_code == 201
        data = res.json()
        record_id = data["id"]
        assert data["title"] == "AI Architecture Deep Dive"
        assert len(data["key_points"]) == 3

    # 2. Query file list
    res_list = client.get("/api/files?timeframe=all")
    assert res_list.status_code == 200
    list_data = res_list.json()
    assert list_data["total"] == 1
    assert list_data["items"][0]["id"] == record_id

    # 3. Get single file record
    res_detail = client.get(f"/api/files/{record_id}")
    assert res_detail.status_code == 200
    assert res_detail.json()["id"] == record_id

    # 4. Download transcript and summary
    res_trans = client.get(f"/api/files/{record_id}/transcript?format=txt")
    assert res_trans.status_code == 200
    assert "In this session" in res_trans.text

    res_sum = client.get(f"/api/files/{record_id}/summary")
    assert res_sum.status_code == 200
    assert "Executive Summary" in res_sum.text

    # 5. Delete file
    res_del = client.delete(f"/api/files/{record_id}")
    assert res_del.status_code == 200
    
    # 6. Verify 404 after deletion
    res_after = client.get(f"/api/files/{record_id}")
    assert res_after.status_code == 404
