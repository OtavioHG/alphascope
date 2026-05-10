from __future__ import annotations

import json
from collections import defaultdict
from typing import Callable

from alphascope.events.event_types import Event
from alphascope.infrastructure.redis_client import InMemoryRedisClient

EventHandler = Callable[[Event], None]


class EventBus:
    def __init__(self, client: InMemoryRedisClient | None = None):
        self.client = client or InMemoryRedisClient()
        self._subscribers: dict[str, list[EventHandler]] = defaultdict(list)

    def publish(self, event: Event) -> Event:
        self.client.publish(
            event.name,
            json.dumps(
                {
                    "name": event.name,
                    "payload": event.payload,
                    "created_at": event.created_at,
                }
            ),
        )
        for handler in self._subscribers.get(event.name, []):
            handler(event)
        return event

    def subscribe(self, event_name: str, handler: EventHandler) -> None:
        self._subscribers[event_name].append(handler)

    def messages(self, event_name: str) -> list[dict]:
        raw_messages = self.client.get_messages(event_name)
        return [json.loads(message) for message in raw_messages]

    def reset(self) -> None:
        self.client.flushall()
        self._subscribers.clear()
