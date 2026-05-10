"""Ranking pipeline for assets."""

from __future__ import annotations

import pandas as pd

from alphascope.core.exceptions import RankingError
from alphascope.ranking.scorer import ensure_score_column, score_assets


class AssetRanker:
    """Generate a sorted asset ranking from latest technical features."""

    def rank(self, features: pd.DataFrame) -> pd.DataFrame:
        if features.empty:
            raise RankingError("Cannot rank empty features")
        scored = ensure_score_column(score_assets(features))
        ranked = scored.sort_values(["score", "momentum"], ascending=[False, False]).reset_index(drop=True)
        ranked["rank"] = range(1, len(ranked) + 1)
        columns = [
            "timestamp",
            "symbol",
            "score",
            "rank",
            "heuristic_score",
            "ml_probability",
            "news_score",
            "market_sentiment_adjustment",
            "momentum_component",
            "volume_component",
            "trend_component",
            "rsi_component",
        ]
        return ranked.loc[:, [column for column in columns if column in ranked.columns]]
