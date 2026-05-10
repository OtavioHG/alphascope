"""External market data package."""

from alphascope.external_data.aggregator import MarketDataAggregator
from alphascope.external_data.base import ExternalMarketSource
from alphascope.external_data.binance_source import BinanceMarketSource
from alphascope.external_data.coinmarketcap_source import CoinMarketCapMarketSource
from alphascope.external_data.coingecko_source import CoinGeckoMarketSource
from alphascope.external_data.schemas import MarketAssetSnapshot, SourceHealthStatus

__all__ = [
    "CoinGeckoMarketSource",
    "CoinMarketCapMarketSource",
    "ExternalMarketSource",
    "MarketAssetSnapshot",
    "MarketDataAggregator",
    "SourceHealthStatus",
    "BinanceMarketSource",
]
