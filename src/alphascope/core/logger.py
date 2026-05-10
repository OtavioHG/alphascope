"""Centralized logging setup."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from alphascope.config.settings import settings


class JsonLogFormatter(logging.Formatter):
    """Render log records as structured JSON lines."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for attribute in ("component", "event", "symbol", "mode"):
            value = getattr(record, attribute, None)
            if value is not None:
                payload[attribute] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


class PlainLogFormatter(logging.Formatter):
    def __init__(self) -> None:
        super().__init__(fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S")



def _build_formatter() -> logging.Formatter:
    return JsonLogFormatter() if settings.log_format == "json" else PlainLogFormatter()



def configure_logging() -> None:
    """Configure root logging once for CLI and pipelines."""
    root_logger = logging.getLogger()
    if getattr(configure_logging, "_configured", False):
        return

    log_file = Path(settings.log_dir) / "alphascope.log"
    formatter = _build_formatter()

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)

    root_logger.setLevel(settings.log_level)
    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    setattr(configure_logging, "_configured", True)



def get_logger(name: str) -> logging.Logger:
    """Return a module logger after base configuration."""
    configure_logging()
    return logging.getLogger(name)
