"""Minimal in-process sliding-window rate limiter.

The service runs as a single Uvicorn worker, so a process-local limiter is
sufficient to blunt brute-force attempts against ``/api/auth/login``. If the
deployment is ever scaled to multiple workers/replicas, move this to the edge
(Caddy) or a shared store; the limiter is not shared across processes.
"""

import time
from collections import defaultdict, deque
from threading import Lock
from typing import Deque, Dict, Optional


class SlidingWindowRateLimiter:
    """Thread-safe fixed-key sliding-window counter.

    Keeps at most ``max_requests`` timestamps per key within ``window_seconds``.
    Empty buckets are pruned so the key map cannot grow without bound.
    """

    def __init__(self, max_requests: int, window_seconds: float, max_keys: int = 10_000):
        if max_requests < 1:
            raise ValueError("max_requests must be >= 1")
        if window_seconds <= 0:
            raise ValueError("window_seconds must be > 0")
        self.max_requests = max_requests
        self.window_seconds = float(window_seconds)
        self.max_keys = max_keys
        self._buckets: Dict[str, Deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def allow(self, key: str) -> bool:
        """Record an attempt for ``key``; return False when over the limit."""
        now = time.monotonic()
        with self._lock:
            # Hard cap on distinct keys to protect memory under IP flooding.
            if key not in self._buckets and len(self._buckets) >= self.max_keys:
                self._prune_empty(now)
                if len(self._buckets) >= self.max_keys:
                    # Cannot track a new key safely; fail closed for the new key.
                    return False

            bucket = self._buckets[key]
            cutoff = now - self.window_seconds
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()

            if len(bucket) >= self.max_requests:
                return False

            bucket.append(now)
            return True

    def _prune_empty(self, now: float) -> None:
        cutoff = now - self.window_seconds
        for k in list(self._buckets.keys()):
            bucket = self._buckets[k]
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            if not bucket:
                del self._buckets[k]


def client_ip_from_request(request) -> str:
    """Best-effort client IP, honouring the Caddy ``X-Forwarded-For`` chain."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        first = forwarded.split(",")[0].strip()
        if first:
            return first
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()
    client = getattr(request, "client", None)
    if client and client.host:
        return client.host
    return "unknown"


def build_login_rate_limiter(max_requests: int, window_seconds: float) -> SlidingWindowRateLimiter:
    return SlidingWindowRateLimiter(max_requests=max_requests, window_seconds=window_seconds)
