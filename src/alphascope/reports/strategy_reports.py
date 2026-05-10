from __future__ import annotations

from pathlib import Path

import pandas as pd


class StrategyReportBuilder:
    def __init__(self, output_dir: str = "data/processed/reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def build(self, strategies: pd.DataFrame, mined_signals: pd.DataFrame) -> dict[str, Path]:
        strategies_path = self.output_dir / "strategy_candidates.csv"
        signals_path = self.output_dir / "mined_signals.csv"
        strategies.to_csv(strategies_path, index=False)
        mined_signals.to_csv(signals_path, index=False)
        return {"strategies_path": strategies_path, "signals_path": signals_path}
