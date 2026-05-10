from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


class RetrainingManager:
    def __init__(self, output_dir: str = "data/processed/evolution"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.retraining_path = self.output_dir / "retraining_events.json"

    def evaluate_trigger(
        self,
        performance_drift: float,
        regime_shift: bool,
        elapsed_windows: int,
    ) -> dict[str, object]:
        should_retrain = performance_drift >= 0.25 or regime_shift or elapsed_windows >= 6
        result = {
            "should_retrain": should_retrain,
            "trigger_reason": "performance_drift" if performance_drift >= 0.25 else "regime_shift" if regime_shift else "time_window" if elapsed_windows >= 6 else "none",
        }
        self.retraining_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
        return result
