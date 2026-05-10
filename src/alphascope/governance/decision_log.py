from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd


class DecisionLog:
    def __init__(self, output_dir: str = "data/processed/governance"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.log_path = self.output_dir / "decision_log.jsonl"

    def record(
        self,
        strategy_id: str,
        previous_status: str,
        new_status: str,
        reason: str,
        metrics_snapshot: dict[str, object],
    ) -> dict[str, object]:
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "strategy_id": strategy_id,
            "previous_status": previous_status,
            "new_status": new_status,
            "reason": reason,
            "metrics_snapshot": metrics_snapshot,
        }
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, default=str) + "\n")
        return payload

    def load(self) -> pd.DataFrame:
        if not self.log_path.exists():
            return pd.DataFrame()
        rows = [json.loads(line) for line in self.log_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        return pd.DataFrame(rows)
