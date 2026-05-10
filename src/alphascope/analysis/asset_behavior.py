from __future__ import annotations

import pandas as pd


class AssetBehaviorAnalyzer:
    def analyze(self, dataset: pd.DataFrame) -> pd.DataFrame:
        if dataset.empty:
            return pd.DataFrame()
        frame = dataset.sort_values(["symbol", "timestamp"]).copy()
        if "pct_return" not in frame.columns:
            frame["pct_return"] = frame.groupby("symbol")["close"].pct_change().fillna(0.0)
        aggregations: dict[str, tuple[str, str]] = {
            "avg_return": ("pct_return", "mean"),
            "volatility": ("pct_return", "std"),
            "avg_volume": ("volume", "mean"),
        }
        if "sentiment_score" in frame.columns:
            aggregations["avg_sentiment"] = ("sentiment_score", "mean")
        if "news_count_window" in frame.columns:
            aggregations["news_intensity"] = ("news_count_window", "mean")
        summary = frame.groupby("symbol").agg(**aggregations).reset_index()
        summary["leadership_score"] = summary["avg_return"].fillna(0.0) - summary["volatility"].fillna(0.0) * 0.5
        return summary.sort_values("leadership_score", ascending=False).reset_index(drop=True)
