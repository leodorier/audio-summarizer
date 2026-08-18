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
