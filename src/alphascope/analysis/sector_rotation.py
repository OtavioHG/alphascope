from __future__ import annotations

import pandas as pd

DEFAULT_SECTOR_MAP = {
    "FETUSDT": "AI",
    "AGIXUSDT": "AI",
    "ARBUSDT": "L2",
    "OPUSDT": "L2",
    "UNIUSDT": "DeFi",
    "AAVEUSDT": "DeFi",
    "DOGEUSDT": "memes",
    "PEPEUSDT": "memes",
    "IMXUSDT": "gaming",
    "GALAUSDT": "gaming",
}


class SectorRotationAnalyzer:
    def __init__(self, sector_map: dict[str, str] | None = None):
        self.sector_map = sector_map or DEFAULT_SECTOR_MAP

    def analyze(self, dataset: pd.DataFrame) -> pd.DataFrame:
        if dataset.empty:
            return pd.DataFrame()
        frame = dataset.copy()
        if "pct_return" not in frame.columns:
            frame["pct_return"] = frame.groupby("symbol")["close"].pct_change().fillna(0.0)
        frame["sector"] = frame["symbol"].map(self.sector_map).fillna("infra")
        aggregations: dict[str, tuple[str, str]] = {
            "avg_return": ("pct_return", "mean"),
            "avg_volume": ("volume", "mean"),
            "asset_count": ("symbol", "nunique"),
        }
        if "sentiment_score" in frame.columns:
            aggregations["avg_sentiment"] = ("sentiment_score", "mean")
        sector_summary = frame.groupby("sector").agg(**aggregations).reset_index()
        sector_summary["avg_sentiment"] = sector_summary.get("avg_sentiment", 0.0)
        sector_summary["rotation_score"] = (
            sector_summary["avg_return"].fillna(0.0) * 100.0
            + sector_summary["avg_sentiment"].fillna(0.0) * 10.0
            + sector_summary["asset_count"].clip(lower=1)
        )
        return sector_summary.sort_values("rotation_score", ascending=False).reset_index(drop=True)
