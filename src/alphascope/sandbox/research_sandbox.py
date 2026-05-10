from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path


class ResearchSandbox:
    def __init__(self, output_dir: str = "data/processed/sandbox"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def create_session(self, name: str, config: dict[str, object]) -> dict[str, object]:
        session_id = f"{name}_{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"
        session_dir = self.output_dir / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        metadata = {"session_id": session_id, "config": config}
        (session_dir / "metadata.json").write_text(json.dumps(metadata, indent=2, default=str), encoding="utf-8")
        return {"session_id": session_id, "path": str(session_dir)}
