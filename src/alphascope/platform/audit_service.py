from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from alphascope.config.settings import settings
from alphascope.storage.repositories import StorageRepository


class AuditService:
    """Persist important operational changes to both DB and jsonl."""

    def __init__(self, repository: StorageRepository | None = None, audit_file: Path | None = None) -> None:
        self.repository = repository or StorageRepository(auto_cleanup=False)
        self.audit_file = audit_file or (settings.runtime_dir / "audit_log.jsonl")
        self.audit_file.parent.mkdir(parents=True, exist_ok=True)

    def record(self, action: str, *, actor: str, source: str, target: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        event = {
            "timestamp": datetime.now(UTC),
            "action": action,
            "actor": actor,
            "source": source,
            "target": target,
            "payload_json": payload or {},
        }
        self.repository.save_audit_event(event)
        serializable = {
            **event,
            "timestamp": event["timestamp"].isoformat(),
        }
        with self.audit_file.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(serializable, default=str) + "\n")
        return serializable
