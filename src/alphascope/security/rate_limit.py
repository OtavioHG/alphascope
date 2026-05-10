from __future__ import annotations

from collections import defaultdict, deque
from datetime import UTC, datetime

try:
    from fastapi import Header, HTTPException, status
except Exception:  # pragma: no cover - optional dependency
    Header = lambda default=None: default  # type: ignore

    class HTTPException(Exception):
        def __init__(self, status_code: int, detail: str):
            super().__init__(detail)
            self.status_code = status_code
            self.detail = detail

    class _Status:
        HTTP_429_TOO_MANY_REQUESTS = 429

    status = _Status()  # type: ignore


class RateLimiter:
    def __init__(self, limit: int = 60, window_seconds: int = 60):
        self.limit = limit
        self.window_seconds = window_seconds
        self._calls: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str) -> None:
        now = datetime.now(UTC).timestamp()
        calls = self._calls[key]
        while calls and now - calls[0] > self.window_seconds:
            calls.popleft()
        if len(calls) >= self.limit:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded")
        calls.append(now)


_default_limiter = RateLimiter()


def rate_limit_dependency(limit: int = 60, window_seconds: int = 60):
    limiter = _default_limiter if (limit, window_seconds) == (_default_limiter.limit, _default_limiter.window_seconds) else RateLimiter(limit, window_seconds)

    def _dependency(x_api_key: str | None = Header(default="anonymous")) -> None:
        limiter.check(x_api_key or "anonymous")

    return _dependency
