from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd


class ModelRunRepository:
    def __init__(self, base_dir: str | Path = "data/processed/models"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.base_dir / "model_runs.jsonl"

    def save_run(self, payload: dict[str, Any]) -> Path:
        record = dict(payload)
        record.setdefault("recorded_at", datetime.now(UTC).isoformat())
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record) + "\n")
        return self.path

    def list_runs(self) -> pd.DataFrame:
        if not self.path.exists():
            return pd.DataFrame()
        rows = [json.loads(line) for line in self.path.read_text(encoding="utf-8").splitlines() if line.strip()]
        return pd.DataFrame(rows)
