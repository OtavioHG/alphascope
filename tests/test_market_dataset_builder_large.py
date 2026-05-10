from __future__ import annotations

from pathlib import Path
import shutil

import pandas as pd
import pytest

from alphascope.config.settings import settings
from alphascope.datasets.market_dataset_builder import MarketDatasetBuilder


class FakeCoinGeckoClient:
    def fetch_market_metrics(self, limit: int = 250) -> pd.DataFrame:
        return pd.DataFrame([{"canonical_symbol": "BTC", "market_cap": 1_000_000.0, "market_rank": 1}])


class FakeCoinMarketCapClient:
    def fetch_market_metrics(self, limit: int = 250) -> pd.DataFrame:
        return pd.DataFrame()


class FakeRepository:
    def get_candles(self, symbol: str, interval: str) -> pd.DataFrame:
        return pd.DataFrame()

    def get_features(self, symbol: str, interval: str) -> pd.DataFrame:
        return pd.DataFrame()


def test_market_dataset_builder_builds_from_external_parquet() -> None:
    pytest.importorskip("pyarrow")
    test_dir = Path("data/test_market_dataset_builder")
    original_data_dir = settings.data_dir
    original_market_path = settings.market_dataset_path_name
    if test_dir.exists():
        shutil.rmtree(test_dir)
    object.__setattr__(settings, "data_dir", test_dir)
    object.__setattr__(settings, "market_dataset_path_name", str((test_dir / "processed" / "market_training_dataset.parquet").as_posix()))
    try:
        settings.external_data_dir.mkdir(parents=True, exist_ok=True)
        rows = []
        base_time = pd.Timestamp("2025-01-01T00:00:00Z")
        for index in range(40):
            rows.append(
                {
                    "timestamp": base_time + pd.Timedelta(hours=index),
                    "open": 100 + index,
                    "high": 101 + index,
                    "low": 99 + index,
                    "close": 100 + (index * 0.5),
                    "volume": 1000 + index,
                    "symbol": "BTCUSDT",
                    "interval": "1h",
                    "source": "external",
                }
            )
        parquet_path = test_dir / "external" / "btc_market.parquet"
        pd.DataFrame(rows).to_parquet(parquet_path, index=False)

        builder = MarketDatasetBuilder(
            repository=FakeRepository(),
            coingecko_client=FakeCoinGeckoClient(),
            coinmarketcap_client=FakeCoinMarketCapClient(),
        )
        dataset = builder.build(
            symbols=["BTCUSDT"],
            interval="1h",
            external_dataset_paths=[parquet_path],
            export=True,
        )

        assert not dataset.empty
        assert {"market_cap", "market_rank", "is_external_source", "btc_correlation_24"}.issubset(dataset.columns)
        assert settings.market_dataset_path.exists()
    finally:
        object.__setattr__(settings, "data_dir", original_data_dir)
        object.__setattr__(settings, "market_dataset_path_name", original_market_path)
        if test_dir.exists():
            shutil.rmtree(test_dir)
