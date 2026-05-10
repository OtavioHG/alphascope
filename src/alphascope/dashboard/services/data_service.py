from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from alphascope.storage.repositories import StorageRepository


class DashboardDataService:
    def __init__(
        self,
        repository: StorageRepository | None = None,
        dataset_path: str | Path | None = None,
        logs_dir: str | Path = "logs",
    ):
        self.repository = repository or StorageRepository()
        self.dataset_path = Path(dataset_path) if dataset_path else None
        self.logs_dir = Path(logs_dir)

    def load_dataset(self) -> pd.DataFrame:
        if self.dataset_path is not None:
            if not self.dataset_path.exists():
                return pd.DataFrame()
            dataset = pd.read_csv(self.dataset_path)
            if "timestamp" in dataset.columns:
                dataset["timestamp"] = pd.to_datetime(dataset["timestamp"], errors="coerce", utc=True)
            return dataset
        ranking = self.repository.get_latest_ranking(interval="1h")
        if not ranking.empty and "timestamp" in ranking.columns:
            ranking["timestamp"] = pd.to_datetime(ranking["timestamp"], errors="coerce", utc=True)
        return ranking

    def get_available_symbols(self) -> list[str]:
        dataset = self.load_dataset()
        if dataset.empty or "symbol" not in dataset.columns:
            return []
        return sorted(dataset["symbol"].dropna().astype(str).unique().tolist())

    def filter_market_data(self, symbol: str | None = None, interval: str | None = None) -> pd.DataFrame:
        if self.dataset_path is not None:
            dataset = self.load_dataset()
            if symbol and not dataset.empty:
                dataset = dataset.loc[dataset["symbol"] == symbol].copy()
            if interval and "interval" in dataset.columns:
                dataset = dataset.loc[dataset["interval"] == interval].copy()
            return dataset.reset_index(drop=True)
        effective_interval = interval or "1h"
        ranking = self.repository.get_latest_ranking(interval=effective_interval)
        if symbol and not ranking.empty:
            ranking = ranking.loc[ranking["symbol"] == symbol].copy()
        return ranking.reset_index(drop=True)

    def load_recent_news(self, limit: int = 100) -> pd.DataFrame:
        path = Path("data/processed/scored_news_latest.csv")
        if not path.exists():
            return pd.DataFrame()
        news_df = pd.read_csv(path)
        if "published_at" in news_df.columns:
            news_df["published_at"] = pd.to_datetime(news_df["published_at"], errors="coerce", utc=True)
        return news_df.head(limit).reset_index(drop=True)

    def load_candles(self, symbol: str, limit: int = 300) -> pd.DataFrame:
        return self.repository.get_candles(symbol=symbol, interval="1h", limit=limit)

    def load_features(self, symbol: str, limit: int = 300) -> pd.DataFrame:
        features = self.repository.get_features(symbol=symbol, interval="1h")
        if not features.empty:
            features = features.tail(limit).reset_index(drop=True)
            if "timestamp" in features.columns:
                features["timestamp"] = pd.to_datetime(features["timestamp"], errors="coerce", utc=True)
        return features

    def load_recent_logs(self, log_name: str, lines: int = 100) -> list[str]:
        path = self.logs_dir / log_name
        if not path.exists():
            return []
        return path.read_text(encoding="utf-8", errors="ignore").splitlines()[-lines:]

    def quick_market_snapshot(self) -> dict[str, Any]:
        dataset = self.load_dataset()
        if dataset.empty:
            return {"assets_analyzed": 0, "market_sentiment": 0.0}
        sentiment_column = "market_sentiment_adjustment" if "market_sentiment_adjustment" in dataset.columns else "sentiment_score"
        sentiment = dataset.get(sentiment_column, pd.Series([0.0])).fillna(0.0).mean()
        return {
            "assets_analyzed": int(dataset["symbol"].nunique()) if "symbol" in dataset.columns else 0,
            "market_sentiment": float(sentiment),
        }
