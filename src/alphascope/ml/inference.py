"""Inference helpers for trained market models."""

from __future__ import annotations

import pandas as pd

from alphascope.config.settings import settings
from alphascope.datasets.market_dataset_builder import MARKET_FEATURE_COLUMNS
from alphascope.features.feature_pipeline import FeaturePipeline
from alphascope.ml.model_registry import ModelRegistry
from alphascope.storage.repositories import StorageRepository


class MarketModelInference:
    """Load a persisted market model and generate probabilities."""

    def __init__(self, repository: StorageRepository | None = None, registry: ModelRegistry | None = None) -> None:
        self.repository = repository or StorageRepository()
        self.feature_pipeline = FeaturePipeline(repository=self.repository)
        self.registry = registry or ModelRegistry()

    def predict_latest(self, symbols: list[str], interval: str) -> pd.DataFrame:
        model = self.registry.load_model(settings.market_model_path)
        rows = []
        for symbol in symbols:
            features = self.repository.get_features(symbol=symbol, interval=interval)
            if features.empty:
                features = self.feature_pipeline.build_for_symbol(symbol=symbol, interval=interval)
            if features.empty:
                continue
            latest = features.sort_values("timestamp").iloc[[-1]].copy()
            for column in MARKET_FEATURE_COLUMNS:
                if column not in latest.columns:
                    latest[column] = float("nan")
                latest[column] = pd.to_numeric(latest[column], errors="coerce")
            probability = float(model.predict_proba(latest.loc[:, MARKET_FEATURE_COLUMNS])[:, 1][0])
            latest["ml_probability"] = probability
            latest["score"] = probability
            rows.append(latest)
        return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()

    def predict_frame(self, features: pd.DataFrame) -> pd.DataFrame:
        if features.empty:
            return pd.DataFrame()
        model = self.registry.load_model(settings.market_model_path)
        scored = features.copy()
        for column in MARKET_FEATURE_COLUMNS:
            if column not in scored.columns:
                scored[column] = float("nan")
            scored[column] = pd.to_numeric(scored[column], errors="coerce")
        scored["ml_probability"] = model.predict_proba(scored.loc[:, MARKET_FEATURE_COLUMNS])[:, 1]
        return scored
