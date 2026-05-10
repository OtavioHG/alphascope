"""Redis-backed cache and pub/sub helpers for multi-agent runtime."""

from __future__ import annotations

import json
from typing import Any

from alphascope.config.settings import settings
from alphascope.infrastructure.redis_client import InMemoryRedisClient
from alphascope.utils.time import utc_now


def _build_client() -> Any:
    try:
        import redis  # type: ignore

        client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
        client.ping()
        return client
    except Exception:
        return InMemoryRedisClient()


class MultiAgentCacheService:
    def __init__(self, client: Any | None = None, *, namespace: str = "alphascope:multi_agent") -> None:
        self.client = client or _build_client()
        self.namespace = namespace.rstrip(":")

    def cache_context(self, symbol: str, timeframe: str, payload: dict[str, Any]) -> None:
        self.set_json(f"context:{symbol.upper()}:{timeframe}", payload)

    def cache_result(self, symbol: str, timeframe: str, payload: dict[str, Any]) -> None:
        self.set_json(f"result:{symbol.upper()}:{timeframe}", payload)
        self.publish_event("decision_events", payload)

    def write_heartbeat(self, payload: dict[str, Any]) -> None:
        heartbeat = {"timestamp": utc_now().isoformat(), **payload}
        self.set_json("heartbeat", heartbeat)
        self.publish_event("heartbeat", heartbeat)

    def read_status(self) -> dict[str, Any]:
        heartbeat = self.get_json("heartbeat") or {}
        return {
            "backend": self.client.__class__.__name__,
            "namespace": self.namespace,
            "heartbeat": heartbeat,
        }

    def publish_event(self, channel: str, payload: dict[str, Any]) -> None:
        serialized = json.dumps(payload, default=str, ensure_ascii=False)
        self.client.publish(self._key(channel), serialized)

    def get_channel_messages(self, channel: str) -> list[dict[str, Any]]:
        if not hasattr(self.client, "get_messages"):
            return []
        messages = self.client.get_messages(self._key(channel))
        parsed: list[dict[str, Any]] = []
        for item in messages:
            try:
                parsed.append(json.loads(item))
            except Exception:
                parsed.append({"raw": item})
        return parsed

    def set_json(self, suffix: str, payload: dict[str, Any], *, ttl_seconds: int | None = 3600) -> None:
        key = self._key(suffix)
        serialized = json.dumps(payload, default=str, ensure_ascii=False)
        if ttl_seconds and hasattr(self.client, "setex"):
            self.client.setex(key, ttl_seconds, serialized)
        else:
            self.client.set(key, serialized)

    def get_json(self, suffix: str) -> dict[str, Any] | None:
        raw = self.client.get(self._key(suffix))
        if raw is None:
            return None
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        if isinstance(raw, str):
            try:
                return json.loads(raw)
            except Exception:
                return {"raw": raw}
        if isinstance(raw, dict):
            return raw
        return {"value": raw}

    def _key(self, suffix: str) -> str:
        return f"{self.namespace}:{suffix}"
