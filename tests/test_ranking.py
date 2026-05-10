from __future__ import annotations

import pandas as pd

from alphascope.config.settings import settings
from alphascope.ranking.ranker import AssetRanker


def test_asset_ranker_orders_highest_score_first():
    frame = pd.DataFrame(
        {
            "symbol": ["BTCUSDT", "ETHUSDT", "SOLUSDT"],
            "timestamp": pd.to_datetime(["2024-01-01T00:00:00Z"] * 3),
            "interval": ["1h"] * 3,
            "close": [100.0, 100.0, 100.0],
            "momentum": [0.08, 0.02, -0.01],
            "relative_volume": [1.9, 1.1, 0.8],
            "trend_strength": [0.05, 0.01, -0.02],
            "rsi": [58.0, 53.0, 71.0],
        }
    )

    ranking = AssetRanker().rank(frame)

    assert ranking["symbol"].tolist() == ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    assert ranking["score"].iloc[0] > ranking["score"].iloc[-1]
    assert ranking["rank"].tolist() == [1, 2, 3]


def test_asset_ranker_hybrid_always_outputs_numeric_score():
    original_mode = settings.ranking_mode
    original_ml = settings.ranking_ml_weight
    original_heuristic = settings.ranking_heuristic_weight
    original_news = settings.ranking_news_weight

    object.__setattr__(settings, "ranking_mode", "hybrid")
    object.__setattr__(settings, "ranking_ml_weight", 0.6)
    object.__setattr__(settings, "ranking_heuristic_weight", 0.2)
    object.__setattr__(settings, "ranking_news_weight", 0.2)

    try:
        frame = pd.DataFrame(
            {
                "symbol": ["BTCUSDT", "ETHUSDT"],
                "timestamp": pd.to_datetime(["2024-01-01T00:00:00Z"] * 2),
                "interval": ["1h"] * 2,
                "close": [100.0, 100.0],
                "momentum": [0.08, 0.02],
                "relative_volume": [1.9, 1.1],
                "trend_strength": [0.05, 0.01],
                "rsi": [58.0, 53.0],
                "ml_probability": [0.91, 0.41],
                "news_score": [0.65, None],
            }
        )

        ranking = AssetRanker().rank(frame)

        assert "score" in ranking.columns
        assert ranking["score"].dtype.kind in {"f", "i"}
        assert ranking["score"].notna().all()
        assert "final_score" not in ranking.columns
        assert ranking["score"].iloc[0] > ranking["score"].iloc[1]
    finally:
        object.__setattr__(settings, "ranking_mode", original_mode)
        object.__setattr__(settings, "ranking_ml_weight", original_ml)
        object.__setattr__(settings, "ranking_heuristic_weight", original_heuristic)
        object.__setattr__(settings, "ranking_news_weight", original_news)
