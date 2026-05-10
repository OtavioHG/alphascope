from __future__ import annotations

import logging

from alphascope.events.event_types import Event

logger = logging.getLogger("alphascope.system")


def log_event(event: Event) -> None:
    logger.info("event=%s payload=%s created_at=%s", event.name, event.payload, event.created_at)
