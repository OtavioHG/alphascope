"""Telegram delivery client for AlphaScope alerts."""

from __future__ import annotations

import queue
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable

import requests

from alphascope.core.logger import get_logger

logger = get_logger(__name__)


@dataclass(slots=True)
class TelegramSendResult:
    delivered: bool
    status_code: int | None = None
    error: str | None = None
    chunks_sent: int = 0


@dataclass(slots=True)
class _TelegramJob:
    payload: dict[str, Any]
    results: list[TelegramSendResult] = field(default_factory=list)
    event: threading.Event = field(default_factory=threading.Event)


class TelegramNotifier:
    """Send operational alerts to Telegram with bounded retries and chunking."""

    def __init__(
        self,
        token: str | None,
        chat_id: str | None,
        *,
        enabled: bool = True,
        parse_mode: str = "Markdown",
        timeout: int = 5,
        retries: int = 3,
        max_message_length: int = 3500,
        post_func: Callable[..., Any] | None = None,
    ) -> None:
        self.token = token
        self.chat_id = chat_id
        self.enabled = enabled
        self.parse_mode = parse_mode
        self.timeout = max(1, timeout)
        self.retries = max(1, retries)
        self.max_message_length = max(1, max_message_length)
        self._post_func = post_func or requests.post
        self._queue: queue.Queue[_TelegramJob | None] = queue.Queue()
        self._stop_event = threading.Event()
        self._worker = threading.Thread(target=self._run_worker, name="alphascope-telegram-notifier", daemon=True)
        self._worker.start()

    @property
    def configured(self) -> bool:
        return self.enabled and bool(self.token) and bool(self.chat_id)

    def send_message(self, message: str, *, chat_id: str | None = None) -> TelegramSendResult:
        if not self.enabled:
            return TelegramSendResult(delivered=False, error="telegram alerts disabled")
        if not self.token or not (chat_id or self.chat_id):
            return TelegramSendResult(delivered=False, error="telegram credentials missing")

        chunks = self._split_message(message)
        results: list[TelegramSendResult] = []
        for chunk in chunks:
            payload = {
                "chat_id": chat_id or self.chat_id,
                "text": chunk,
                "parse_mode": self.parse_mode,
                "disable_web_page_preview": True,
            }
            job = _TelegramJob(payload=payload)
            self._queue.put(job)
            job.event.wait(timeout=(self.timeout + 1) * self.retries + 5)
            if not job.results:
                results.append(TelegramSendResult(delivered=False, error="telegram worker timeout"))
                continue
            results.extend(job.results)

        delivered = all(item.delivered for item in results) if results else False
        error = next((item.error for item in results if item.error), None)
        status_code = next((item.status_code for item in reversed(results) if item.status_code is not None), None)
        return TelegramSendResult(
            delivered=delivered,
            status_code=status_code,
            error=error,
            chunks_sent=sum(1 for item in results if item.delivered),
        )

    def close(self) -> None:
        self._stop_event.set()
        self._queue.put(None)
        if self._worker.is_alive():
            self._worker.join(timeout=2)

    def _run_worker(self) -> None:
        while not self._stop_event.is_set():
            job = self._queue.get()
            if job is None:
                self._queue.task_done()
                break
            try:
                result = self._deliver_payload(job.payload)
                job.results.append(result)
            except Exception as exc:  # pragma: no cover - defensive guard
                logger.exception("Telegram worker crashed while delivering a message")
                job.results.append(TelegramSendResult(delivered=False, error=str(exc)))
            finally:
                job.event.set()
                self._queue.task_done()

    def _deliver_payload(self, payload: dict[str, Any]) -> TelegramSendResult:
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        last_error: str | None = None
        last_status_code: int | None = None
        for attempt in range(1, self.retries + 1):
            response: Any | None = None
            try:
                response = self._post_func(url, json=payload, timeout=self.timeout)
                if hasattr(response, "raise_for_status"):
                    response.raise_for_status()
                logger.info(
                    "Telegram message sent chat_id=%s size=%s attempt=%s",
                    payload.get("chat_id"),
                    len(str(payload.get("text", ""))),
                    attempt,
                )
                return TelegramSendResult(delivered=True, status_code=getattr(response, "status_code", None))
            except Exception as exc:
                last_status_code = getattr(getattr(exc, "response", None), "status_code", None)
                if last_status_code is None:
                    last_status_code = getattr(response, "status_code", None)
                if last_status_code == 400 and payload.get("parse_mode"):
                    logger.warning("Telegram send failed with parse_mode=%s; retrying as plain text", payload.get("parse_mode"))
                    payload = {key: value for key, value in payload.items() if key != "parse_mode"}
                    continue
                last_error = str(exc)
                logger.warning(
                    "Telegram send failed chat_id=%s attempt=%s/%s status=%s error=%s",
                    payload.get("chat_id"),
                    attempt,
                    self.retries,
                    last_status_code,
                    last_error,
                )
                if attempt < self.retries:
                    time.sleep(min(attempt, 3))
        return TelegramSendResult(delivered=False, status_code=last_status_code, error=last_error)

    def _split_message(self, message: str) -> list[str]:
        text = (message or "").strip()
        if not text:
            return [""]
        if len(text) <= self.max_message_length:
            return [text]

        chunks: list[str] = []
        current = ""
        for line in text.splitlines():
            candidate = line if not current else f"{current}\n{line}"
            if len(candidate) <= self.max_message_length:
                current = candidate
                continue
            if current:
                chunks.append(current)
            if len(line) <= self.max_message_length:
                current = line
                continue
            start = 0
            while start < len(line):
                end = start + self.max_message_length
                chunks.append(line[start:end])
                start = end
            current = ""
        if current:
            chunks.append(current)
        return chunks or [text[: self.max_message_length]]
