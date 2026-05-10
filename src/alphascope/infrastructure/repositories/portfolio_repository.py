from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


class PortfolioRepository:
    def __init__(self, base_dir: str | Path = "data/processed/paper_trades"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.snapshot_path = self.base_dir / "portfolio_snapshot.json"
        self.positions_path = self.base_dir / "open_positions.csv"

    def save_snapshot(self, snapshot: dict[str, Any]) -> Path:
        self.snapshot_path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
        return self.snapshot_path

    def load_snapshot(self) -> dict[str, Any]:
        if not self.snapshot_path.exists():
            return {}
        return json.loads(self.snapshot_path.read_text(encoding="utf-8"))

    def save_positions(self, positions: list[dict[str, Any]]) -> Path:
        frame = pd.DataFrame(
            positions,
            columns=[
                "symbol",
                "quantity",
                "entry_price",
                "entry_fee",
                "opened_at",
                "stop_loss_price",
                "take_profit_price",
            ],
        )
        frame.to_csv(self.positions_path, index=False)
        return self.positions_path

    def load_positions(self) -> pd.DataFrame:
        if not self.positions_path.exists():
            return pd.DataFrame()
        return pd.read_csv(self.positions_path)
