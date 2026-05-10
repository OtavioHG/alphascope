from __future__ import annotations

from pathlib import Path
import shutil

import pandas as pd

from alphascope.config.settings import settings
from alphascope.core.pipeline import AlphaScopePipeline


def test_show_news_signals_aggregates_by_asset() -> None:
    test_dir = Path("data/test_news_signals")
    original_data_dir = settings.data_dir
    original_lookback = settings.ranking_news_lookback_hours
    if test_dir.exists():
        shutil.rmtree(test_dir)
    object.__setattr__(settings, "data_dir", test_dir)
    object.__setattr__(settings, "ranking_news_lookback_hours", 72)
    try:
        settings.processed_data_dir.mkdir(parents=True, exist_ok=True)
        now = pd.Timestamp.now(tz="UTC")
        frame = pd.DataFrame(
            [
                {
                    "timestamp": (now - pd.Timedelta(hours=3)).isoformat(),
                    "related_asset": "BTC",
                    "sentiment_score": 0.8,
                    "impact_score": 0.6,
                },
                {
                    "timestamp": (now - pd.Timedelta(hours=1)).isoformat(),
                    "related_asset": "BTC",
                    "sentiment_score": 0.7,
                    "impact_score": 0.4,
                },
                {
                    "timestamp": (now - pd.Timedelta(hours=2)).isoformat(),
                    "related_asset": "ETH",
                    "sentiment_score": 0.4,
                    "impact_score": 0.5,
                },
            ]
        )
        frame.to_csv(settings.scored_news_path, index=False)

        summary = AlphaScopePipeline().show_news_signals()

        assert set(summary["related_asset"]) == {"BTC", "ETH"}
        btc_row = summary.loc[summary["related_asset"] == "BTC"].iloc[0]
        assert btc_row["news_count"] == 2
        assert round(float(btc_row["news_score"]), 4) == 0.625
    finally:
        object.__setattr__(settings, "data_dir", original_data_dir)
        object.__setattr__(settings, "ranking_news_lookback_hours", original_lookback)
        if test_dir.exists():
            shutil.rmtree(test_dir)
