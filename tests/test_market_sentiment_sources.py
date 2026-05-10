from __future__ import annotations

from datetime import UTC, datetime

import pandas as pd

from alphascope.data_sources.cryptocompare_client import CryptoCompareMarketDataClient
from alphascope.data_sources.fear_greed_client import FearGreedIndexClient
from alphascope.datasets.market_dataset_builder import MarketDatasetBuilder
from alphascope.ranking.scorer import adjust_score_with_market_sentiment


class FakeRepository:
    def get_candles(self, symbol: str, interval: str) -> pd.DataFrame:
        base = pd.Timestamp("2025-01-01T00:00:00Z")
        return pd.DataFrame(
            [
                {
                    "timestamp": base + pd.Timedelta(hours=index),
                    "open": 100.0 + index,
                    "high": 101.0 + index,
                    "low": 99.0 + index,
                    "close": 100.5 + index,
                    "volume": 1_000.0 + index,
                    "symbol": symbol,
                    "interval": interval,
                }
                for index in range(30)
            ]
        )

    def get_features(self, symbol: str, interval: str) -> pd.DataFrame:
        base = pd.Timestamp("2025-01-01T00:00:00Z")
        return pd.DataFrame(
            [
                {
                    "timestamp": base + pd.Timedelta(hours=index),
                    "symbol": symbol,
                    "interval": interval,
                    "close": 100.5 + index,
                    "return_pct": 0.01,
                    "ma_short": 100.0,
                    "ma_long": 99.0,
                    "rsi": 52.0,
                    "volatility": 0.03,
                    "avg_volume": 1_000.0,
                    "relative_volume": 1.1,
                    "momentum": 0.02,
                    "trend_strength": 0.03,
                }
                for index in range(30)
            ]
        )


class FakeCoinGeckoClient:
    def fetch_market_metrics(self, limit: int = 250) -> pd.DataFrame:
        return pd.DataFrame([{"canonical_symbol": "BTC", "market_cap": 1_000_000.0, "market_rank": 1}])


class FakeCoinMarketCapClient:
    def fetch_market_metrics(self, limit: int = 250) -> pd.DataFrame:
        return pd.DataFrame()


class FakeCryptoCompareClient:
    def fetch_market_snapshot(self, symbols: list[str], *, quote_symbol: str = "USD") -> pd.DataFrame:
        return pd.DataFrame(
            [
                {
                    "timestamp": datetime.now(UTC),
                    "canonical_symbol": "BTC",
                    "symbol": "BTC",
                    "quote_asset": quote_symbol,
                    "price": 65000.0,
                    "volume_24h": 2_000_000.0,
                    "market_cap": 1_200_000_000_000.0,
                    "supply": 19_000_000.0,
                    "source": "cryptocompare",
                }
            ]
        )

    def fetch_hourly_history(self, symbol: str, *, quote_symbol: str = "USD", limit: int = 2000, exchange: str | None = None) -> pd.DataFrame:
        return pd.DataFrame()

    def fetch_daily_history(self, symbol: str, *, quote_symbol: str = "USD", limit: int = 2000, exchange: str | None = None) -> pd.DataFrame:
        return pd.DataFrame()


class FakeFearGreedClient:
    def fetch_fear_greed_index(self, *, limit: int = 30) -> pd.DataFrame:
        base = pd.Timestamp("2024-12-31T00:00:00Z")
        return pd.DataFrame(
            [
                {
                    "timestamp": base + pd.Timedelta(days=index),
                    "fear_greed_value": 20.0,
                    "fear_greed_label": "Extreme Fear",
                }
                for index in range(10)
            ]
        )


def test_cryptocompare_client_normalizes_hourly_history() -> None:
    client = CryptoCompareMarketDataClient()
    client._request_json = lambda path, params=None: {  # type: ignore[method-assign]
        "Data": {
            "Data": [
                {"time": 1735689600, "open": 100, "high": 110, "low": 95, "close": 105, "volumefrom": 10, "volumeto": 1050},
                {"time": 1735693200, "open": 105, "high": 111, "low": 101, "close": 108, "volumefrom": 12, "volumeto": 1296},
            ]
        }
    }

    frame = client.fetch_hourly_history("BTC", quote_symbol="USD", limit=2)

    assert len(frame) == 2
    assert frame.loc[0, "symbol"] == "BTCUSD"
    assert frame.loc[0, "interval"] == "1h"
    assert frame.loc[1, "close"] == 108


def test_fear_greed_client_normalizes_response() -> None:
    client = FearGreedIndexClient()
    client._request_json = lambda params=None: {  # type: ignore[method-assign]
        "data": [
            {"value": "73", "value_classification": "Greed", "timestamp": "1735689600"},
            {"value": "25", "value_classification": "Extreme Fear", "timestamp": "1735603200"},
        ]
    }

    frame = client.fetch_fear_greed_index(limit=2)

    assert len(frame) == 2
    assert frame.loc[0, "fear_greed_label"] == "Extreme Fear"
    assert frame.loc[1, "fear_greed_value"] == 73


def test_market_dataset_builder_attaches_fear_greed_and_cryptocompare_metadata() -> None:
    builder = MarketDatasetBuilder(
        repository=FakeRepository(),
        cryptocompare_client=FakeCryptoCompareClient(),
        coingecko_client=FakeCoinGeckoClient(),
        coinmarketcap_client=FakeCoinMarketCapClient(),
        fear_greed_client=FakeFearGreedClient(),
    )

    dataset = builder.build(symbols=["BTCUSDT"], interval="1h", export=False)

    assert not dataset.empty
    assert {"fear_greed_value", "fear_greed_label", "cryptocompare_market_cap", "cryptocompare_supply"}.issubset(dataset.columns)
    assert dataset["fear_greed_label"].iloc[0] == "Extreme Fear"
    assert dataset["cryptocompare_supply"].iloc[0] == 19_000_000.0


def test_adjust_score_with_market_sentiment_applies_contrarian_shift() -> None:
    dataset = pd.DataFrame(
        [
            {"symbol": "BTCUSDT", "score": 0.60, "fear_greed_value": 20.0, "fear_greed_label": "Extreme Fear"},
            {"symbol": "ETHUSDT", "score": 0.60, "fear_greed_value": 80.0, "fear_greed_label": "Extreme Greed"},
        ]
    )

    adjusted = adjust_score_with_market_sentiment(dataset)

    assert adjusted.loc[0, "score"] > 0.60
    assert adjusted.loc[1, "score"] < 0.60
    assert "market_sentiment_adjustment" in adjusted.columns
