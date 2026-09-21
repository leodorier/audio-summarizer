from app.rate_limit import SlidingWindowRateLimiter, client_ip_from_request


def test_limiter_blocks_after_max_requests():
    limiter = SlidingWindowRateLimiter(max_requests=3, window_seconds=60)
    assert limiter.allow("a") is True
    assert limiter.allow("a") is True
    assert limiter.allow("a") is True
    assert limiter.allow("a") is False


def test_limiter_keys_are_independent():
    limiter = SlidingWindowRateLimiter(max_requests=1, window_seconds=60)
    assert limiter.allow("a") is True
    assert limiter.allow("b") is True
    assert limiter.allow("a") is False


class _FakeClient:
    def __init__(self, host):
        self.host = host


class _FakeRequest:
    def __init__(self, headers=None, host="10.0.0.1"):
        self.headers = headers or {}
        self.client = _FakeClient(host) if host else None


def test_client_ip_prefers_x_forwarded_for():
    req = _FakeRequest(headers={"x-forwarded-for": "203.0.113.5, 10.0.0.1"})
    assert client_ip_from_request(req) == "203.0.113.5"


def test_client_ip_falls_back_to_socket_peer():
    req = _FakeRequest(host="10.0.0.7")
    assert client_ip_from_request(req) == "10.0.0.7"
