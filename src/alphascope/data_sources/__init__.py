"""Market data source clients for AlphaScope."""

from alphascope.data_sources.binance_client import BinanceMarketDataClient
from alphascope.data_sources.cryptocompare_client import CryptoCompareMarketDataClient
from alphascope.data_sources.coingecko_client import CoinGeckoDataClient
from alphascope.data_sources.coinmarketcap_client import CoinMarketCapDataClient
from alphascope.data_sources.fear_greed_client import FearGreedIndexClient

__all__ = [
    "BinanceMarketDataClient",
    "CryptoCompareMarketDataClient",
    "CoinGeckoDataClient",
    "CoinMarketCapDataClient",
    "FearGreedIndexClient",
]
