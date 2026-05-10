from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd


class ExperimentTracker:
    def __init__(self, output_dir: str = "data/processed/experiments"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.runs_path = self.output_dir / "experiment_runs.jsonl"

    def track(
        self,
        strategy_id: str,
        feature_set: list[str],
        target_definition: dict[str, object],
        metrics: dict[str, object],
        promotion_status: str = "research_only",
        train_period: str = "historical",
        test_period: str = "forward_slice",
        dataset_hash: str | None = None,
        dataset_window: dict[str, object] | None = None,
        model_name: str | None = None,
        hyperparameters: dict[str, object] | None = None,
        backtest_summary: dict[str, object] | None = None,
        experiment_type: str = "research",
    ) -> dict[str, object]:
        payload = {
            "experiment_id": f"exp_{datetime.now(UTC).strftime('%Y%m%d%H%M%S%f')}",
            "strategy_id": strategy_id,
            "feature_set": feature_set,
            "target_definition": target_definition,
            "train_period": train_period,
            "test_period": test_period,
            "metrics": metrics,
            "promotion_status": promotion_status,
            "dataset_hash": dataset_hash,
            "dataset_window": dataset_window or {},
            "model_name": model_name,
            "hyperparameters": hyperparameters or {},
            "backtest_summary": backtest_summary or {},
            "experiment_type": experiment_type,
            "tracked_at": datetime.now(UTC).isoformat(),
        }
        with self.runs_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, default=str) + "\n")
        return payload

    def load(self) -> pd.DataFrame:
        if not self.runs_path.exists():
            return pd.DataFrame()
        rows = [
            json.loads(line)
            for line in self.runs_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        return pd.DataFrame(rows)
