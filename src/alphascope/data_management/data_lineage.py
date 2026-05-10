from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd


class DataLineageTracker:
    def __init__(self, output_dir: str = "data/processed/lineage"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.lineage_path = self.output_dir / "data_lineage.jsonl"

    def record(
        self,
        dataset_hash: str,
        features_used: list[str],
        model_version: str | None = None,
        strategy_id: str | None = None,
        source: str = "pipeline",
    ) -> dict[str, object]:
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "dataset_hash": dataset_hash,
            "features_used": features_used,
            "model_version": model_version,
            "strategy_id": strategy_id,
            "source": source,
        }
        with self.lineage_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload) + "\n")
        return payload

    def load(self) -> pd.DataFrame:
        if not self.lineage_path.exists():
            return pd.DataFrame()
        rows = [json.loads(line) for line in self.lineage_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        return pd.DataFrame(rows)
