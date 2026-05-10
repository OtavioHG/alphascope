from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd


class DatasetVersionManager:
    def __init__(self, output_dir: str = "data/processed/datasets"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.registry_path = self.output_dir / "dataset_versions.jsonl"

    def register(
        self,
        dataset: pd.DataFrame,
        dataset_name: str,
        features_used: list[str],
        temporal_window: dict[str, object],
    ) -> dict[str, object]:
        dataset_hash = self.compute_hash(dataset)
        payload = {
            "dataset_name": dataset_name,
            "dataset_hash": dataset_hash,
            "features_used": features_used,
            "temporal_window": temporal_window,
            "rows": int(len(dataset)),
            "columns": list(dataset.columns),
        }
        with self.registry_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, default=str) + "\n")
        dataset.to_csv(self.output_dir / f"{dataset_name}_{dataset_hash[:12]}.csv", index=False)
        return payload

    def load(self) -> pd.DataFrame:
        if not self.registry_path.exists():
            return pd.DataFrame()
        rows = [
            json.loads(line)
            for line in self.registry_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        return pd.DataFrame(rows)

    @staticmethod
    def compute_hash(dataset: pd.DataFrame) -> str:
        csv_bytes = dataset.to_csv(index=False).encode("utf-8")
        return hashlib.sha256(csv_bytes).hexdigest()
