"""Generic event loop for long-running simulation tasks."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Callable, TypeVar

T = TypeVar("T")


@dataclass(slots=True)
class EventLoopConfig:
    """Configuration for repeated event-loop execution."""

    cycle_interval_seconds: int
    run_forever: bool = True
    duration_minutes: int | None = None


class EventLoop:
    """Run a callable repeatedly until stopped or until a deadline."""

    def __init__(self, config: EventLoopConfig) -> None:
        self.config = config
        self._stop_event = threading.Event()

    def run(self, callback: Callable[[], T], *, max_cycles: int | None = None, stop_event: threading.Event | None = None) -> list[T]:
        """Execute the callback on each cycle."""
        loop_stop = stop_event or self._stop_event
        results: list[T] = []
        started_at = datetime.now(UTC)
        deadline = None if self.config.run_forever or self.config.duration_minutes is None else started_at + timedelta(minutes=self.config.duration_minutes)

        while not loop_stop.is_set():
            cycle_started = time.monotonic()
            results.append(callback())
            if max_cycles is not None and len(results) >= max_cycles:
                break
            if deadline is not None and datetime.now(UTC) >= deadline:
                break
            elapsed = time.monotonic() - cycle_started
            sleep_seconds = max(0.0, self.config.cycle_interval_seconds - elapsed)
            if sleep_seconds > 0:
                time.sleep(sleep_seconds)
        return results

    def stop(self) -> None:
        """Stop the running event loop."""
        self._stop_event.set()
