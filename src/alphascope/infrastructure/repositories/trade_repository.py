from __future__ import annotations

from pathlib import Path

import pandas as pd


class TradeRepository:
    def __init__(self, base_dir: str | Path = "data/processed/paper_trades"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.base_dir / "trades.csv"

    def append_trade(self, trade: dict) -> Path:
        frame = pd.DataFrame([trade])
        if self.path.exists():
            frame.to_csv(self.path, mode="a", header=False, index=False)
        else:
            frame.to_csv(self.path, index=False)
        return self.path

    def load_trades(self) -> pd.DataFrame:
        if not self.path.exists():
            return pd.DataFrame()
        return pd.read_csv(self.path)
