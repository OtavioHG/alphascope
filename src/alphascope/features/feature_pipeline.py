"""Feature generation pipeline."""

from __future__ import annotations

import pandas as pd

from alphascope.config.settings import settings
from alphascope.core.exceptions import FeatureError
from alphascope.core.logger import get_logger
from alphascope.features.technical import compute_technical_features
from alphascope.storage.repositories import StorageRepository

logger = get_logger(__name__)


class FeaturePipeline:
    """Compute and persist technical features from stored candles."""

    def __init__(self, repository: StorageRepository | None = None) -> None:
        self.repository = repository or StorageRepository()

    def build_for_symbol(self, symbol: str, interval: str) -> pd.DataFrame:
        candles = self.repository.get_candles(symbol=symbol, interval=interval)
        if candles.empty:
            raise FeatureError(f"No candles available for {symbol} {interval}")

        features = compute_technical_features(
            candles=candles,
            short_window=settings.short_window,
            long_window=settings.long_window,
            rsi_window=settings.rsi_window,
            volatility_window=settings.volatility_window,
            volume_window=settings.volume_window,
            momentum_window=settings.momentum_window,
        )
        saved = self.repository.save_features(features)
        logger.info("Saved %s feature rows for %s %s", saved, symbol, interval)
        return features

    @staticmethod
    def latest_cross_section(features_by_symbol: list[pd.DataFrame]) -> pd.DataFrame:
        rows = []
        for frame in features_by_symbol:
            if not frame.empty:
                rows.append(frame.sort_values("timestamp").iloc[-1])
        return pd.DataFrame(rows).reset_index(drop=True)

    @staticmethod
    def consolidate_dataset(candles_df: pd.DataFrame, tech_df: pd.DataFrame, news_df: pd.DataFrame) -> pd.DataFrame:
        base = candles_df.copy()
        if base.empty:
            return base
        if not tech_df.empty:
            base = base.merge(tech_df, on=[column for column in ["timestamp", "symbol"] if column in tech_df.columns], how="left")
        if not news_df.empty and "published_at" in news_df.columns:
            sentiment_avg = float(pd.to_numeric(news_df.get("sentiment_score"), errors="coerce").dropna().mean())
            if pd.isna(sentiment_avg):
                sentiment_avg = 0.0
            base["sentiment_avg"] = sentiment_avg
        else:
            base["sentiment_avg"] = 0.0
        return base.sort_values("timestamp").reset_index(drop=True)
