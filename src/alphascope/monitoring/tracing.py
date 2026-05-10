from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class JsonTracer:
    def __init__(self, service: str = "alphascope-core", output_path: str = "logs/system.jsonl"):
        self.service = service
        self.output_path = Path(output_path)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, event: str, status: str, **kwargs: Any) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "service": self.service,
            "event": event,
            "status": status,
        }
        payload.update(kwargs)
        with self.output_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, default=str) + "\n")
        return payload
