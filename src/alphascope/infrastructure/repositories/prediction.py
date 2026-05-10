from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd


class PredictionRepository:
    def __init__(self, base_dir: str | Path = "data/processed/predictions"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.base_dir / "predictions.jsonl"
        self.rankings_dir = Path("data/processed/rankings")
        self.rankings_dir.mkdir(parents=True, exist_ok=True)
        self.rankings_path = self.rankings_dir / "rankings.jsonl"

    def save_predictions(self, predictions_df: pd.DataFrame, name: str) -> Path:
        csv_path = self.base_dir / f"{name}.csv"
        predictions_df.to_csv(csv_path, index=False)
        with self.path.open("a", encoding="utf-8") as handle:
            for row in predictions_df.to_dict(orient="records"):
                row["saved_at"] = datetime.now(UTC).isoformat()
                handle.write(json.dumps(row, default=str) + "\n")
        return csv_path

    def save_ranking(self, ranking_df: pd.DataFrame, name: str) -> Path:
        csv_path = self.rankings_dir / f"{name}.csv"
        ranking_df.to_csv(csv_path, index=False)
        with self.rankings_path.open("a", encoding="utf-8") as handle:
            for row in ranking_df.to_dict(orient="records"):
                row["saved_at"] = datetime.now(UTC).isoformat()
                handle.write(json.dumps(row, default=str) + "\n")
        return csv_path
