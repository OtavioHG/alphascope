"""Compatibility wrapper for the new datasets.market_dataset_builder module."""

from __future__ import annotations

import pandas as pd

from alphascope.config.settings import settings
from alphascope.datasets.market_dataset_builder import MARKET_FEATURE_COLUMNS, MarketDatasetBuilder as _MarketDatasetBuilder

FEATURE_COLUMNS = MARKET_FEATURE_COLUMNS


class MarketDatasetBuilder(_MarketDatasetBuilder):
    """Backwards-compatible wrapper exposing train/test split and legacy imports."""

    def train_test_split(
        self,
        dataset: pd.DataFrame,
        train_fraction: float | None = None,
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        if dataset.empty:
            return pd.DataFrame(), pd.DataFrame()
        fraction = train_fraction or settings.training_train_fraction
        ordered = dataset.sort_values(["timestamp", "symbol"]).reset_index(drop=True)
        split_index = max(1, int(len(ordered) * fraction))
        train = ordered.iloc[:split_index].reset_index(drop=True)
        test = ordered.iloc[split_index:].reset_index(drop=True)
        return train, test
