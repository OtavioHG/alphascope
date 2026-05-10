from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from alphascope.monitoring.metrics import compute_trading_metrics
from alphascope.storage.repositories import StorageRepository


class TradingService:
    def __init__(
        self,
        repository: StorageRepository | None = None,
        trades_dir: str | Path | None = None,
        backtests_dir: str | Path | None = None,
    ):
        self.repository = repository or StorageRepository()
        self.trades_dir = Path(trades_dir) if trades_dir else None
        self.backtests_dir = Path(backtests_dir) if backtests_dir else None

    def load_trades(self) -> pd.DataFrame:
        if self.trades_dir is not None:
            trades_path = self.trades_dir / "trades.csv"
            if not trades_path.exists():
                return pd.DataFrame()
            trades = pd.read_csv(trades_path)
        else:
            trades = self.repository.get_trade_history(limit=500)
        if not trades.empty:
            timestamp_col = "entry_time" if "entry_time" in trades.columns else "timestamp"
            trades[timestamp_col] = pd.to_datetime(trades[timestamp_col], errors="coerce", utc=True)
        return trades

    def load_portfolio_snapshot(self) -> dict[str, Any]:
        if self.trades_dir is not None:
            snapshot_path = self.trades_dir / "portfolio_snapshot.json"
            return json.loads(snapshot_path.read_text(encoding="utf-8")) if snapshot_path.exists() else {}
        snapshot = self.repository.get_latest_snapshot()
        return snapshot or {}

    def load_open_positions(self) -> pd.DataFrame:
        return self.repository.get_open_positions()

    def calculate_metrics(self) -> dict[str, Any]:
        trades = self.load_trades()
        snapshot = self.load_portfolio_snapshot()
        metrics = compute_trading_metrics(trades)
        metrics["capital"] = float(snapshot.get("available_balance", snapshot.get("cash_balance", snapshot.get("cash", 0.0)))) if snapshot else 0.0
        metrics["equity"] = float(snapshot.get("total_equity", snapshot.get("equity", 0.0))) if snapshot else 0.0
        positions_json = snapshot.get("positions_json", {}) if snapshot else {}
        metrics["open_positions"] = snapshot.get("open_positions", len(positions_json) if isinstance(positions_json, dict) else 0)
        metrics["drawdown"] = float(snapshot.get("drawdown", 0.0)) if snapshot else 0.0
        metrics["profit_factor"] = float(snapshot.get("profit_factor", 0.0)) if snapshot else 0.0
        metrics["win_rate_live"] = float(snapshot.get("win_rate", metrics.get("win_rate", 0.0))) if snapshot else float(metrics.get("win_rate", 0.0))
        return metrics

    def load_retraining_runs(self) -> pd.DataFrame:
        return self.repository.get_retraining_runs(limit=50)

    def load_model_versions(self) -> pd.DataFrame:
        return self.repository.get_model_versions(limit=50)

    def load_signal_history(self) -> pd.DataFrame:
        return self.repository.get_signal_history(limit=200)

    def load_equity_curve(self) -> pd.DataFrame:
        if self.backtests_dir is not None:
            curve_files = sorted(self.backtests_dir.glob("*_equity_curve.csv"), key=lambda item: item.stat().st_mtime)
            if not curve_files:
                return pd.DataFrame()
            curve = pd.read_csv(curve_files[-1])
        else:
            curve = self.repository.get_portfolio_analytics_snapshots(limit=300)
        if not curve.empty and "timestamp" in curve.columns:
            curve["timestamp"] = pd.to_datetime(curve["timestamp"], errors="coerce", utc=True)
        return curve
