"""Heartbeat utilities for long-running AlphaScope processes."""

from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

from alphascope.core.logger import get_logger

logger = get_logger(__name__)

HeartbeatPayloadProvider = Callable[[], dict[str, Any]]


@dataclass(slots=True)
class HeartbeatConfig:
    """Configuration for runtime heartbeat emission."""

    interval_seconds: int
    heartbeat_file: Path


class HeartbeatService:
    """Persist runtime heartbeat metadata on a fixed interval."""

    def __init__(
        self,
        config: HeartbeatConfig,
        *,
        payload_provider: HeartbeatPayloadProvider | None = None,
    ) -> None:
        self.config = config
        self.payload_provider = payload_provider or (lambda: {})
        self.config.heartbeat_file.parent.mkdir(parents=True, exist_ok=True)
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        """Start the heartbeat background loop."""
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, name="alphascope-heartbeat", daemon=True)
        self._thread.start()
        logger.info("Heartbeat service started")

    def stop(self, timeout_seconds: float = 5.0) -> None:
        """Stop the heartbeat background loop."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=timeout_seconds)
        self.write_once(status="stopped")
        logger.info("Heartbeat service stopped")

    def write_once(self, *, status: str = "running") -> None:
        """Write a single heartbeat payload immediately."""
        payload = {
            "status": status,
            "timestamp": datetime.now(UTC).isoformat(),
            "process_id": os.getpid(),
            **self.payload_provider(),
        }
        self.config.heartbeat_file.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    def _run(self) -> None:
        while not self._stop_event.is_set():
            self.write_once(status="running")
            time.sleep(max(1, self.config.interval_seconds))
