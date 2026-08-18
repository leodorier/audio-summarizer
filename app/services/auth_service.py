import os
import time
import httpx
from typing import Optional, Dict, Any, Tuple, List
from app.config import settings

# In-memory session cache: token -> (user_dict, expires_timestamp)
_SESSION_CACHE: Dict[str, Tuple[Dict[str, Any], float]] = {}
CACHE_TTL_SECONDS = 60.0

def _get_api_urls() -> List[str]:
    urls = []
    if settings.BETTER_AUTH_API_URL:
        urls.append(settings.BETTER_AUTH_API_URL)
    if settings.FALLBACK_AUTH_API_URL and settings.FALLBACK_AUTH_API_URL not in urls:
        urls.append(settings.FALLBACK_AUTH_API_URL)
    return urls

def verify_session(cookies: Dict[str, str], headers: Dict[str, str]) -> Optional[Dict[str, Any]]:
    """
    Verifies incoming session against Better Auth.
    Supports in-memory TTL caching of verified session tokens.
    """
    if not settings.AUTH_ENABLED:
        return {"id": "dev-user", "email": "admin@leolab.app", "name": "Admin (Dev Mode)"}

    # Extract session token from cookies or Authorization header
    token = (
        cookies.get("better-auth.session_token")
        or cookies.get("__Secure-better-auth.session_token")
        or cookies.get("session_token")
    )
    if not token and "authorization" in headers:
        auth_hdr = headers["authorization"]
        if auth_hdr.startswith("Bearer "):
            token = auth_hdr[7:]

    # Check local cache first
    now = time.time()
    if token and token in _SESSION_CACHE:
        user_info, exp = _SESSION_CACHE[token]
        if now < exp:
            return user_info
        else:
            del _SESSION_CACHE[token]

    # Build cookie string
    cookie_str = "; ".join([f"{k}={v}" for k, v in cookies.items()])
    fwd_headers = {
        "User-Agent": "AudioSummarizer-FastAPI/1.0",
        "Accept": "application/json",
    }
    if cookie_str:
        fwd_headers["Cookie"] = cookie_str
    if "authorization" in headers:
        fwd_headers["Authorization"] = headers["authorization"]

    for base_url in _get_api_urls():
        try:
            url = f"{base_url.rstrip('/')}/api/auth/get-session"
            with httpx.Client(timeout=4.0) as client:
                res = client.get(url, headers=fwd_headers)
                if res.status_code == 200:
                    data = res.json()
                    if data and isinstance(data, dict) and "user" in data:
                        user = data["user"]
                        actor = {
                            "id": user.get("id"),
                            "email": user.get("email"),
                            "name": user.get("name") or user.get("email", "").split("@")[0],
                        }
                        if token:
                            _SESSION_CACHE[token] = (actor, now + CACHE_TTL_SECONDS)
                        return actor
        except Exception:
            continue

    return None

def sign_in_better_auth(email: str, password: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str], list]:
    """
    Submits credentials to Better Auth sign-in endpoint.
    Returns (success, user_data, error_message, cookies_to_set)
    """
    payload = {"email": email, "password": password}

    for base_url in _get_api_urls():
        try:
            url = f"{base_url.rstrip('/')}/api/auth/sign-in/email"
            with httpx.Client(timeout=6.0) as client:
                res = client.post(url, json=payload, headers={"Accept": "application/json"})
                if res.status_code == 200:
                    data = res.json()
                    user = data.get("user") if isinstance(data, dict) else None
                    
                    # Extract set-cookie headers from response
                    raw_cookies = res.headers.get_list("set-cookie")
                    return True, user, None, raw_cookies
                elif res.status_code in (400, 401):
                    try:
                        err = res.json().get("message", "Invalid email or password.")
                    except Exception:
                        err = "Invalid email or password."
                    return False, None, err, []
        except Exception:
            continue

    return False, None, "Authentication service unreachable. Please try again.", []
