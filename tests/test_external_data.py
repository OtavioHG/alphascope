from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import shutil

import pandas as pd

from alphascope.external_data.aggregator import MarketDataAggregator
from alphascope.external_data.binance_source import BinanceMarketSource
from alphascope.external_data.coinmarketcap_source import CoinMarketCapMarketSource
from alphascope.external_data.coingecko_source import CoinGeckoMarketSource
from alphascope.external_data.normalizers import canonicalize_asset_symbol, split_binance_symbol
from alphascope.config.settings import settings


class FakeSource:
    def __init__(self, frame: pd.DataFrame) -> None:
        self.frame = frame

    def fetch_market_snapshot(self, limit: int = 250) -> pd.DataFrame:
        return self.frame.head(limit).copy()


def test_normalizers_map_symbols_and_split_binance_pairs() -> None:
    assert canonicalize_asset_symbol("bitcoin") == "BTC"
    assert canonicalize_asset_symbol("eth", "Ethereum") == "ETH"
    assert split_binance_symbol("BTCUSDT") == ("BTC", "USDT")
    assert split_binance_symbol("ETHBTC") == ("ETH", "BTC")


def test_binance_market_source_normalizes_market_snapshot() -> None:
    source = BinanceMarketSource()
    source._request_json = lambda path, params=None, headers=None: [  # type: ignore[method-assign]
        {
            "symbol": "BTCUSDT",
            "lastPrice": "64000.12",
            "quoteVolume": "123456789.0",
            "priceChangePercent": "2.5",
            "count": 1000,
        }
    ]

    frame = source.fetch_market_snapshot(limit=1)

    assert len(frame) == 1
    assert frame.loc[0, "source"] == "binance"
    assert frame.loc[0, "base_asset"] == "BTC"
    assert frame.loc[0, "quote_asset"] == "USDT"
    assert frame.loc[0, "canonical_symbol"] == "BTC"
    assert frame.loc[0, "price"] == 64000.12


def test_market_data_aggregator_consolidates_with_primary_priority_and_persists() -> None:
    aggregator = MarketDataAggregator()
    temp_dir = Path("data/test_market_universe")
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    temp_dir.mkdir(parents=True, exist_ok=True)
    aggregator.data_dir = temp_dir

    timestamp = datetime.now(UTC)
    binance_frame = pd.DataFrame(
        [
            {
                "source": "binance",
                "symbol": "BTC/USDT",
                "base_asset": "BTC",
                "quote_asset": "USDT",
                "price": 65000.0,
                "volume_24h": 1000000.0,
                "market_cap": None,
                "rank": None,
                "timestamp": timestamp,
                "raw_symbol": "BTCUSDT",
                "canonical_symbol": "BTC",
                "exchange": "binance",
                "extra_metadata": {},
            }
        ]
    )
    coingecko_frame = pd.DataFrame(
        [
            {
                "source": "coingecko",
                "symbol": "BTC",
                "base_asset": "BTC",
                "quote_asset": "USD",
                "price": 64950.0,
                "volume_24h": 900000.0,
                "market_cap": 1200000000000.0,
                "rank": 1,
                "timestamp": timestamp,
                "raw_symbol": "bitcoin",
                "canonical_symbol": "BTC",
                "exchange": None,
                "extra_metadata": {},
            },
            {
                "source": "coingecko",
                "symbol": "ETH",
                "base_asset": "ETH",
                "quote_asset": "USD",
                "price": 3500.0,
                "volume_24h": 500000.0,
                "market_cap": 400000000000.0,
                "rank": 2,
                "timestamp": timestamp,
                "raw_symbol": "ethereum",
                "canonical_symbol": "ETH",
                "exchange": None,
                "extra_metadata": {},
            },
        ]
    )

    aggregator.sources = {
        "binance": FakeSource(binance_frame),
        "coingecko": FakeSource(coingecko_frame),
    }

    universe = aggregator.fetch_market_universe(
        primary_source="binance",
        fallback_sources=["coingecko"],
        limit=10,
        persist=True,
    )

    assert set(universe["canonical_symbol"]) == {"BTC", "ETH"}
    assert universe.loc[universe["canonical_symbol"] == "BTC", "source"].iloc[0] == "binance"
    assert (temp_dir / "market_universe_latest.csv").exists()
    assert (temp_dir / "binance_snapshot_latest.csv").exists()
    assert (temp_dir / "coingecko_snapshot_latest.csv").exists()
    shutil.rmtree(temp_dir)


def test_market_data_aggregator_compares_sources_for_single_symbol() -> None:
    aggregator = MarketDataAggregator()
    timestamp = datetime.now(UTC)
    aggregator.sources = {
        "binance": FakeSource(
            pd.DataFrame(
                [
                    {
                        "source": "binance",
                        "symbol": "BTC/USDT",
                        "base_asset": "BTC",
                        "quote_asset": "USDT",
                        "price": 65000.0,
                        "volume_24h": 1000000.0,
                        "market_cap": None,
                        "rank": None,
                        "timestamp": timestamp,
                        "raw_symbol": "BTCUSDT",
                        "canonical_symbol": "BTC",
                        "exchange": "binance",
                        "extra_metadata": {},
                    }
                ]
            )
        ),
        "coingecko": FakeSource(
            pd.DataFrame(
                [
                    {
                        "source": "coingecko",
                        "symbol": "BTC",
                        "base_asset": "BTC",
                        "quote_asset": "USD",
                        "price": 64950.0,
                        "volume_24h": 900000.0,
                        "market_cap": 1200000000000.0,
                        "rank": 1,
                        "timestamp": timestamp,
                        "raw_symbol": "bitcoin",
                        "canonical_symbol": "BTC",
                        "exchange": None,
                        "extra_metadata": {},
                    }
                ]
            )
        ),
    }

    comparison = aggregator.compare_sources(symbol="BTC", limit=10)

    assert len(comparison) == 2
    assert comparison["canonical_symbol"].unique().tolist() == ["BTC"]
    assert set(comparison["source"]) == {"binance", "coingecko"}


def test_coingecko_market_source_normalizes_snapshot() -> None:
    source = CoinGeckoMarketSource()
    source._request_json = lambda path, params=None, headers=None: [  # type: ignore[method-assign]
        {
            "id": "bitcoin",
            "symbol": "btc",
            "name": "Bitcoin",
            "current_price": 64000.0,
            "total_volume": 20000000000.0,
            "market_cap": 1200000000000.0,
            "market_cap_rank": 1,
            "image": "https://assets.coingecko.com/coins/images/1/large/bitcoin.png",
            "price_change_percentage_24h": 3.2,
        }
    ]

    frame = source.fetch_market_snapshot(limit=1)

    assert len(frame) == 1
    assert frame.loc[0, "source"] == "coingecko"
    assert frame.loc[0, "canonical_symbol"] == "BTC"
    assert frame.loc[0, "market_cap"] == 1200000000000.0
    assert frame.loc[0, "rank"] == 1


def test_coinmarketcap_market_source_normalizes_snapshot() -> None:
    original_api_key = settings.coinmarketcap_api_key
    original_enabled = settings.enable_coinmarketcap
    object.__setattr__(settings, "coinmarketcap_api_key", "demo-key")
    object.__setattr__(settings, "enable_coinmarketcap", True)
    try:
        source = CoinMarketCapMarketSource()
        source._request_json = lambda path, params=None, headers=None: {  # type: ignore[method-assign]
            "data": [
                {
                    "symbol": "ETH",
                    "name": "Ethereum",
                    "slug": "ethereum",
                    "cmc_rank": 2,
                    "circulating_supply": 120000000.0,
                    "quote": {
                        "USD": {
                            "price": 3500.0,
                            "volume_24h": 15000000000.0,
                            "market_cap": 420000000000.0,
                            "percent_change_24h": 2.1,
                        }
                    },
                }
            ]
        }

        frame = source.fetch_market_snapshot(limit=1)

        assert len(frame) == 1
        assert frame.loc[0, "source"] == "coinmarketcap"
        assert frame.loc[0, "canonical_symbol"] == "ETH"
        assert frame.loc[0, "price"] == 3500.0
        assert frame.loc[0, "rank"] == 2
    finally:
        object.__setattr__(settings, "coinmarketcap_api_key", original_api_key)
        object.__setattr__(settings, "enable_coinmarketcap", original_enabled)


def test_external_source_healthcheck_reports_success_and_failure() -> None:
    source = BinanceMarketSource()
    source.fetch_market_snapshot = lambda limit=1: pd.DataFrame([{"symbol": "BTC/USDT"}])  # type: ignore[method-assign]

    ok_status = source.healthcheck()

    assert ok_status.source == "binance"
    assert ok_status.available is True

    failing_source = BinanceMarketSource()

    def _raise(limit: int = 1) -> pd.DataFrame:
        raise RuntimeError("down")

    failing_source.fetch_market_snapshot = _raise  # type: ignore[method-assign]
    fail_status = failing_source.healthcheck()

    assert fail_status.source == "binance"
    assert fail_status.available is False
    assert fail_status.detail == "down"
