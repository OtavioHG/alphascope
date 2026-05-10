from __future__ import annotations

import json
from collections import defaultdict
from typing import Any


class InMemoryRedisClient:
    _shared_store: dict[str, Any] = {}
    _shared_pubsub: dict[str, list[str]] = defaultdict(list)

    def __init__(self):
        self._store = self._shared_store
        self._pubsub = self._shared_pubsub

    def ping(self) -> bool:
        return True

    def publish(self, channel: str, message: str) -> int:
        self._pubsub[channel].append(message)
        return len(self._pubsub[channel])

    def get_messages(self, channel: str) -> list[str]:
        return list(self._pubsub[channel])

    def set(self, key: str, value: Any) -> None:
        self._store[key] = value

    def setex(self, key: str, ttl_seconds: int, value: Any) -> None:
        _ = ttl_seconds
        self._store[key] = value

    def get(self, key: str) -> Any:
        return self._store.get(key)

    def delete(self, key: str) -> None:
        self._store.pop(key, None)

    def flushall(self) -> None:
        self._store.clear()
        self._pubsub.clear()
