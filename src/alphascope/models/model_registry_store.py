from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd


class ModelRegistryStore:
    def __init__(self, output_dir: str = "data/processed/models"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.registry_path = self.output_dir / "model_registry.jsonl"

    def register(
        self,
        model_name: str,
        model_version: str,
        hyperparameters: dict[str, object],
        dataset_hash: str,
        metrics: dict[str, object],
        artifact_path: str | None = None,
    ) -> dict[str, object]:
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "model_name": model_name,
            "model_version": model_version,
            "hyperparameters": hyperparameters,
            "dataset_hash": dataset_hash,
            "metrics": metrics,
            "artifact_path": artifact_path,
        }
        with self.registry_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, default=str) + "\n")
        return payload

    def load(self) -> pd.DataFrame:
        if not self.registry_path.exists():
            return pd.DataFrame()
        rows = [json.loads(line) for line in self.registry_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        return pd.DataFrame(rows)
