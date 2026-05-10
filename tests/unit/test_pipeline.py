from __future__ import annotations

import pandas as pd

from alphascope.features.pipeline import FeaturePipeline


def test_consolidate_dataset():
    candles_df = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(["2024-01-01 00:00:00+00:00", "2024-01-01 01:00:00+00:00"]),
            "symbol": ["BTCUSDT", "BTCUSDT"],
            "open": [100, 101],
            "high": [101, 102],
            "low": [99, 100],
            "close": [100, 101],
            "volume": [1000, 1200],
            "interval": ["1h", "1h"],
        }
    )
    tech_df = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(["2024-01-01 00:00:00+00:00", "2024-01-01 01:00:00+00:00"]),
            "symbol": ["BTCUSDT", "BTCUSDT"],
            "rsi": [50, 55],
            "momentum": [0.0, 0.01],
        }
    )
    news_df = pd.DataFrame(
        {
            "published_at": pd.to_datetime(["2024-01-01 00:30:00+00:00"]),
            "sentiment_score": [0.8],
            "news_id": [10],
        }
    )

    result = FeaturePipeline.consolidate_dataset(candles_df, tech_df, news_df)

    assert len(result) == 2
    assert "rsi" in result.columns
    assert "sentiment_avg" in result.columns
    assert result["sentiment_avg"].iloc[0] == 0.8
