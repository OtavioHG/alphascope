from __future__ import annotations

import time
from typing import Callable, TypeVar

T = TypeVar("T")


class RetryEngine:
    def __init__(self, retries: int = 3, backoff_seconds: float = 0.1):
        self.retries = retries
        self.backoff_seconds = backoff_seconds

    def run(self, fn: Callable[[], T]) -> T:
        last_error: Exception | None = None
        for attempt in range(self.retries):
            try:
                return fn()
            except Exception as exc:
                last_error = exc
                if attempt == self.retries - 1:
                    break
                time.sleep(self.backoff_seconds * (attempt + 1))
        assert last_error is not None
        raise last_error
