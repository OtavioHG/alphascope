"""Project-wide constants for AlphaScope V1."""

from __future__ import annotations

DEFAULT_SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
DEFAULT_INTERVAL = "1h"
DEFAULT_CANDLE_LIMIT = 500

BINANCE_KLINES_ENDPOINT = "/api/v3/klines"
BINANCE_ALLOWED_INTERVALS = {
    "1m",
    "3m",
    "5m",
    "15m",
    "30m",
    "1h",
    "2h",
    "4h",
    "6h",
    "8h",
    "12h",
    "1d",
}

MARKET_CANDLE_COLUMNS = [
    "timestamp",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "symbol",
    "interval",
]

TECHNICAL_FEATURE_COLUMNS = [
    "timestamp",
    "symbol",
    "interval",
    "close",
    "return_pct",
    "ma_short",
    "ma_long",
    "rsi",
    "volatility",
    "avg_volume",
    "relative_volume",
    "momentum",
    "trend_strength",
]
