import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings
from app.services.auth_service import verify_session, sign_in_better_auth

@pytest.fixture
def client(temp_storage):
    return TestClient(app)

def test_auth_me_unauthenticated(client, monkeypatch):
    monkeypatch.setattr(settings, "AUTH_ENABLED", True)
    with patch("app.main.verify_session", return_value=None):
        res = client.get("/api/auth/me")
        assert res.status_code == 200
        data = res.json()
        assert data["authenticated"] is False
        assert data["user"] is None

def test_auth_me_authenticated(client, monkeypatch):
    monkeypatch.setattr(settings, "AUTH_ENABLED", True)
    mock_user = {"id": "user_123", "email": "leo@leolab.app", "name": "Leo"}
    with patch("app.main.verify_session", return_value=mock_user):
        res = client.get("/api/auth/me", cookies={"better-auth.session_token": "valid_token"})
        assert res.status_code == 200
        data = res.json()
        assert data["authenticated"] is True
        assert data["user"]["email"] == "leo@leolab.app"

def test_auth_login_success(client):
    mock_user = {"id": "user_123", "email": "leo@leolab.app", "name": "Leo"}
    mock_cookies = ["better-auth.session_token=secret_token; Path=/; HttpOnly"]
    with patch("app.main.sign_in_better_auth", return_value=(True, mock_user, None, mock_cookies)):
        res = client.post("/api/auth/login", json={"email": "leo@leolab.app", "password": "password123"})
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["user"]["email"] == "leo@leolab.app"
        assert "better-auth.session_token" in res.headers.get("set-cookie", "")

def test_auth_login_failure(client):
    with patch("app.main.sign_in_better_auth", return_value=(False, None, "Invalid credentials", [])):
        res = client.post("/api/auth/login", json={"email": "wrong@leolab.app", "password": "wrong"})
        assert res.status_code == 401
        data = res.json()
        assert data["success"] is False
        assert data["error"] == "Invalid credentials"

def test_auth_logout(client):
    res = client.post("/api/auth/logout")
    assert res.status_code == 200
    assert res.json()["success"] is True

def test_protected_routes_require_auth(client, monkeypatch):
    monkeypatch.setattr(settings, "AUTH_ENABLED", True)
    with patch("app.main.verify_session", return_value=None):
        # Stats route should return 401
        res = client.get("/api/stats")
        assert res.status_code == 401
        
        # Files list should return 401
        res_files = client.get("/api/files")
        assert res_files.status_code == 401


def test_verify_gemini_settings_endpoint(client):
    """Verify that /api/settings/verify-gemini validates API keys properly."""
    mock_actor = {"id": "dev-user", "name": "dragstonium", "is_owner": True}
    with patch("app.main.verify_session", return_value=mock_actor):
        res = client.post("/api/settings/verify-gemini", json={"api_key": ""})
        assert res.status_code in (200, 400)
        assert "valid" in res.json()


def test_non_owner_upload_blocked_without_key(client, sample_audio_file):
    """Verify that a non-owner operator cannot upload without a custom Gemini API key."""
    non_owner = {
        "id": "regular-user",
        "email": "nils@example.com",
        "name": "Nils",
        "username": "nils",
        "is_owner": False
    }
    with patch("app.main.verify_session", return_value=non_owner):
        with open(sample_audio_file, "rb") as f:
            res = client.post(
                "/api/upload",
                files={"file": ("speech.mp3", f, "audio/mp3")},
                data={"title": "Test Non Owner"}
            )
        assert res.status_code == 428
        assert "Clé API Google Gemini requise" in res.json()["detail"]


def test_non_owner_upload_allowed_with_custom_key(client, sample_audio_file, mock_extraction):
    """Verify that a non-owner operator with custom key succeeds."""
    non_owner = {
        "id": "regular-user",
        "email": "nils@example.com",
        "name": "Nils",
        "username": "nils",
        "is_owner": False
    }
    with patch("app.main.verify_session", return_value=non_owner):
        mock_res = {
            "id": 999, "title": "Test Allowed", "original_filename": "speech.mp3",
            "file_size": 1024, "duration_seconds": 120, "audio_format": "mp3",
            "audio_file_path": "storage/uploads/speech.mp3",
            "transcript_path": "storage/transcripts/speech.txt",
            "transcript_file_path": "storage/transcripts/speech.txt",
            "summary_path": "storage/summaries/speech.md",
            "summary_file_path": "storage/summaries/speech.md",
            "language": "en", "topics": ["test"], "key_points": ["point"], "action_items": [],
            "raw_transcript": "transcript", "summary_text": "summary",
            "created_at": "2026-08-18T00:00:00Z", "updated_at": "2026-08-18T00:00:00Z"
        }
        with patch("app.main.process_audio_file", return_value=mock_res):
            with open(sample_audio_file, "rb") as f:
                res = client.post(
                    "/api/upload",
                    files={"file": ("speech.mp3", f, "audio/mp3")},
                    data={"title": "Test Non Owner", "api_key": "test_personal_key"}
                )
            assert res.status_code == 201
            assert res.json()["title"] == "Test Allowed"
