"""Binance market data client."""

from __future__ import annotations

from time import sleep
from typing import Any

import pandas as pd
import requests

from alphascope.config.constants import BINANCE_ALLOWED_INTERVALS, BINANCE_KLINES_ENDPOINT, MARKET_CANDLE_COLUMNS
from alphascope.config.settings import settings
from alphascope.core.exceptions import IngestionError
from alphascope.core.logger import get_logger
from alphascope.external_data.normalizers import canonicalize_asset_symbol, safe_float, split_binance_symbol
from alphascope.utils.time import from_milliseconds

logger = get_logger(__name__)


class BinanceMarketDataClient:
    """Simple client for Binance public market endpoints."""

    def __init__(
        self,
        base_url: str | None = None,
        timeout: int | None = None,
        max_retries: int | None = None,
        session: requests.Session | None = None,
    ) -> None:
        self.base_url = (base_url or settings.binance_base_url).rstrip("/")
        self.timeout = timeout or settings.request_timeout
        self.max_retries = max_retries or settings.request_retries
        self.session = session or requests.Session()

    def fetch_klines(self, symbol: str, interval: str, limit: int) -> pd.DataFrame:
        """Fetch OHLCV candles normalized to the AlphaScope schema."""
        if interval not in BINANCE_ALLOWED_INTERVALS:
            raise IngestionError(f"Unsupported Binance interval: {interval}")
        payload = self._request_json(
            BINANCE_KLINES_ENDPOINT,
            params={"symbol": symbol.upper(), "interval": interval, "limit": int(limit)},
        )
        rows = []
        for item in payload:
            rows.append(
                {
                    "timestamp": from_milliseconds(int(item[0])),
                    "open": float(item[1]),
                    "high": float(item[2]),
                    "low": float(item[3]),
                    "close": float(item[4]),
                    "volume": float(item[5]),
                    "symbol": symbol.upper(),
                    "interval": interval,
                }
            )
        return pd.DataFrame(rows, columns=MARKET_CANDLE_COLUMNS).sort_values("timestamp").reset_index(drop=True)

    def fetch_ticker_snapshot(self, limit: int = 250) -> pd.DataFrame:
        """Fetch 24h ticker data normalized for market comparisons."""
        payload = self._request_json("/api/v3/ticker/24hr")
        rows = []
        for item in payload[:limit]:
            base_asset, quote_asset = split_binance_symbol(str(item["symbol"]))
            rows.append(
                {
                    "source": "binance",
                    "symbol": f"{base_asset}/{quote_asset}",
                    "base_asset": base_asset,
                    "quote_asset": quote_asset,
                    "canonical_symbol": canonicalize_asset_symbol(base_asset),
                    "price": safe_float(item.get("lastPrice")),
                    "volume_24h": safe_float(item.get("quoteVolume")),
                    "market_cap": None,
                    "market_rank": None,
                    "raw_symbol": str(item["symbol"]),
                    "exchange": "binance",
                }
            )
        return pd.DataFrame(rows)

    def fetch_supported_assets(self, limit: int = 1000) -> pd.DataFrame:
        """Fetch the tradeable asset list from Binance exchange info."""
        payload = self._request_json("/api/v3/exchangeInfo")
        rows = []
        for item in payload.get("symbols", [])[:limit]:
            base_asset = str(item.get("baseAsset", "")).upper()
            quote_asset = str(item.get("quoteAsset", "")).upper()
            rows.append(
                {
                    "symbol": str(item.get("symbol", "")),
                    "base_asset": base_asset,
                    "quote_asset": quote_asset,
                    "canonical_symbol": canonicalize_asset_symbol(base_asset),
                    "status": item.get("status"),
                }
            )
        return pd.DataFrame(rows)

    def _request_json(self, path: str, params: dict[str, Any] | None = None) -> Any:
        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.session.get(f"{self.base_url}{path}", params=params, timeout=self.timeout)
                response.raise_for_status()
                return response.json()
            except (requests.RequestException, ValueError) as exc:
                last_error = exc
                logger.warning("Binance request failed on attempt %s/%s: %s", attempt, self.max_retries, exc)
                if attempt < self.max_retries:
                    sleep(0.5 * attempt)
        raise IngestionError("Binance request failed") from last_error
