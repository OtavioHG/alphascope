from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd


class BacktestRepository:
    def __init__(self, base_dir: str | Path = "data/processed/backtests"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.runs_path = self.base_dir / "backtest_runs.jsonl"
        self.trades_path = self.base_dir / "backtest_trades.jsonl"

    def save_run(self, summary: dict[str, Any], equity_curve_df: pd.DataFrame, name: str) -> dict[str, Path]:
        summary_path = self.base_dir / f"{name}_summary.json"
        equity_path = self.base_dir / f"{name}_equity_curve.csv"
        summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        equity_curve_df.to_csv(equity_path, index=False)
        with self.runs_path.open("a", encoding="utf-8") as handle:
            payload = dict(summary)
            payload["saved_at"] = datetime.now(UTC).isoformat()
            handle.write(json.dumps(payload, default=str) + "\n")
        return {"summary_path": summary_path, "equity_curve_path": equity_path}

    def save_trades(self, trades_df: pd.DataFrame, name: str) -> Path:
        trades_path = self.base_dir / f"{name}_trades.csv"
        trades_df.to_csv(trades_path, index=False)
        with self.trades_path.open("a", encoding="utf-8") as handle:
            for row in trades_df.to_dict(orient="records"):
                row["saved_at"] = datetime.now(UTC).isoformat()
                handle.write(json.dumps(row, default=str) + "\n")
        return trades_path
