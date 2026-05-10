from __future__ import annotations

import shutil
from pathlib import Path

import pandas as pd

from alphascope.config.settings import settings
from alphascope.core.pipeline import AlphaScopePipeline
from alphascope.storage.repositories import StorageRepository


def test_explain_ranking_includes_news_and_ml_contributions() -> None:
    test_dir = Path("data/test_ranking_explain")
    original_data_dir = settings.data_dir
    original_sqlite = settings.sqlite_path
    original_mode = settings.ranking_mode
    original_news_weight = settings.ranking_news_weight
    original_ml_weight = settings.ranking_ml_weight
    original_heuristic_weight = settings.ranking_heuristic_weight
    if test_dir.exists():
        shutil.rmtree(test_dir)
    object.__setattr__(settings, "data_dir", test_dir)
    object.__setattr__(settings, "sqlite_path", test_dir / "alphascope.db")
    object.__setattr__(settings, "ranking_mode", "hybrid")
    object.__setattr__(settings, "ranking_news_weight", 0.2)
    object.__setattr__(settings, "ranking_ml_weight", 0.6)
    object.__setattr__(settings, "ranking_heuristic_weight", 0.2)
    try:
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        settings.processed_data_dir.mkdir(parents=True, exist_ok=True)
        frame = pd.DataFrame(
            [
                {
                    "timestamp": pd.Timestamp.now(tz="UTC").isoformat(),
                    "related_asset": "BTC",
                    "sentiment_score": 0.8,
                    "impact_score": 0.5,
                }
            ]
        )
        frame.to_csv(settings.scored_news_path, index=False)

        features = pd.DataFrame(
            [
                {
                    "timestamp": pd.Timestamp.now(tz="UTC"),
                    "symbol": "BTCUSDT",
                    "interval": "1h",
                    "close": 60000.0,
                    "return_pct": 0.01,
                    "ma_short": 59500.0,
                    "ma_long": 58000.0,
                    "rsi": 58.0,
                    "volatility": 0.02,
                    "avg_volume": 1000.0,
                    "relative_volume": 1.5,
                    "momentum": 0.08,
                    "trend_strength": 0.04,
                    "ml_probability": 0.75,
                }
            ]
        )

        pipeline = AlphaScopePipeline(repository=StorageRepository())
        pipeline._build_rank_cross_section = lambda symbols, interval: features.copy()  # type: ignore[method-assign]
        explanation = pipeline.explain_ranking(["BTCUSDT"], "1h")

        assert "heuristic_contribution" in explanation.columns
        assert "ml_contribution" in explanation.columns
        assert "news_contribution" in explanation.columns
        assert round(float(explanation.loc[0, "ml_contribution"]), 4) == 0.45
    finally:
        object.__setattr__(settings, "data_dir", original_data_dir)
        object.__setattr__(settings, "sqlite_path", original_sqlite)
        object.__setattr__(settings, "ranking_mode", original_mode)
        object.__setattr__(settings, "ranking_news_weight", original_news_weight)
        object.__setattr__(settings, "ranking_ml_weight", original_ml_weight)
        object.__setattr__(settings, "ranking_heuristic_weight", original_heuristic_weight)
        if test_dir.exists():
            shutil.rmtree(test_dir)
