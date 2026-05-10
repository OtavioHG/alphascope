from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


class StrategyVersioning:
    def __init__(self, output_dir: str = "data/processed/lifecycle"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.versions_path = self.output_dir / "strategy_versions.csv"

    def load(self) -> pd.DataFrame:
        if not self.versions_path.exists():
            return pd.DataFrame(columns=["strategy_id", "parent_strategy_id", "version", "changes", "lineage"])
        return pd.read_csv(self.versions_path)

    def create_version(
        self,
        strategy_id: str,
        parent_strategy_id: str | None,
        version: int,
        changes: dict[str, object],
    ) -> pd.DataFrame:
        frame = self.load()
        lineage = parent_strategy_id or strategy_id
        record = {
            "strategy_id": strategy_id,
            "parent_strategy_id": parent_strategy_id,
            "version": version,
            "changes": json.dumps(changes, default=str),
            "lineage": lineage,
        }
        frame = pd.concat([frame, pd.DataFrame([record])], ignore_index=True)
        frame.to_csv(self.versions_path, index=False)
        return frame

    def compare_versions(self, strategy_id: str, previous_strategy_id: str) -> dict[str, object]:
        frame = self.load()
        current = frame.loc[frame["strategy_id"] == strategy_id]
        previous = frame.loc[frame["strategy_id"] == previous_strategy_id]
        if current.empty or previous.empty:
            return {}
        return {
            "strategy_id": strategy_id,
            "previous_strategy_id": previous_strategy_id,
            "current_version": int(current.iloc[-1]["version"]),
            "previous_version": int(previous.iloc[-1]["version"]),
            "changes": json.loads(str(current.iloc[-1]["changes"])),
        }
