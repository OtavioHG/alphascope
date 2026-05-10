"""CryptoCompare market data client."""

from __future__ import annotations

from datetime import UTC, datetime
from time import sleep
from typing import Any

import pandas as pd
import requests

from alphascope.config.settings import settings
from alphascope.core.logger import get_logger

logger = get_logger(__name__)


class CryptoCompareMarketDataClient:
    """Client for CryptoCompare public market endpoints."""

    def __init__(
        self,
        base_url: str | None = None,
        timeout: int | None = None,
        max_retries: int | None = None,
        session: requests.Session | None = None,
    ) -> None:
        self.base_url = (base_url or settings.cryptocompare_base_url).rstrip("/")
        self.timeout = timeout or settings.request_timeout
        self.max_retries = max_retries or settings.request_retries
        self.session = session or requests.Session()

    def fetch_hourly_history(
        self,
        symbol: str,
        *,
        quote_symbol: str = "USD",
        limit: int = 2000,
        exchange: str | None = None,
    ) -> pd.DataFrame:
        """Fetch hourly OHLCV history for one asset."""
        return self._fetch_history(
            endpoint="/data/v2/histohour",
            symbol=symbol,
            quote_symbol=quote_symbol,
            limit=limit,
            exchange=exchange,
            interval="1h",
        )

    def fetch_daily_history(
        self,
        symbol: str,
        *,
        quote_symbol: str = "USD",
        limit: int = 2000,
        exchange: str | None = None,
    ) -> pd.DataFrame:
        """Fetch daily OHLCV history for one asset."""
        return self._fetch_history(
            endpoint="/data/v2/histoday",
            symbol=symbol,
            quote_symbol=quote_symbol,
            limit=limit,
            exchange=exchange,
            interval="1d",
        )

    def fetch_market_snapshot(self, symbols: list[str], *, quote_symbol: str = "USD") -> pd.DataFrame:
        """Fetch a compact market snapshot for multiple assets."""
        normalized_symbols = sorted({item.strip().upper() for item in symbols if item.strip()})
        if not normalized_symbols:
            return pd.DataFrame()
        payload = self._request_json(
            "/data/pricemultifull",
            params={"fsyms": ",".join(normalized_symbols), "tsyms": quote_symbol.upper()},
        )
        raw = payload.get("RAW", {})
        rows = []
        snapshot_at = datetime.now(UTC)
        for symbol in normalized_symbols:
            quote = raw.get(symbol, {}).get(quote_symbol.upper(), {})
            if not quote:
                continue
            rows.append(
                {
                    "timestamp": snapshot_at,
                    "canonical_symbol": symbol,
                    "symbol": symbol,
                    "quote_asset": quote_symbol.upper(),
                    "price": float(quote["PRICE"]) if quote.get("PRICE") is not None else None,
                    "volume_24h": float(quote["TOTALVOLUME24HTO"]) if quote.get("TOTALVOLUME24HTO") is not None else None,
                    "market_cap": float(quote["MKTCAP"]) if quote.get("MKTCAP") is not None else None,
                    "supply": float(quote["SUPPLY"]) if quote.get("SUPPLY") is not None else None,
                    "source": "cryptocompare",
                }
            )
        return pd.DataFrame(rows)

    def _fetch_history(
        self,
        *,
        endpoint: str,
        symbol: str,
        quote_symbol: str,
        limit: int,
        exchange: str | None,
        interval: str,
    ) -> pd.DataFrame:
        payload = self._request_json(
            endpoint,
            params={
                "fsym": symbol.upper(),
                "tsym": quote_symbol.upper(),
                "limit": int(limit),
                **({"e": exchange} if exchange else {}),
            },
        )
        rows = payload.get("Data", {}).get("Data", [])
        frame = pd.DataFrame(rows)
        if frame.empty:
            return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume", "symbol", "interval", "source"])
        frame["timestamp"] = pd.to_datetime(frame["time"], unit="s", utc=True, errors="coerce")
        frame["open"] = pd.to_numeric(frame.get("open"), errors="coerce")
        frame["high"] = pd.to_numeric(frame.get("high"), errors="coerce")
        frame["low"] = pd.to_numeric(frame.get("low"), errors="coerce")
        frame["close"] = pd.to_numeric(frame.get("close"), errors="coerce")
        frame["volume"] = pd.to_numeric(frame.get("volumeto", frame.get("volumefrom")), errors="coerce")
        frame["symbol"] = f"{symbol.upper()}{quote_symbol.upper()}"
        frame["interval"] = interval
        frame["source"] = "cryptocompare"
        return (
            frame.loc[:, ["timestamp", "open", "high", "low", "close", "volume", "symbol", "interval", "source"]]
            .dropna(subset=["timestamp", "open", "high", "low", "close", "volume"])
            .drop_duplicates(subset=["timestamp", "symbol", "interval"], keep="last")
            .sort_values("timestamp")
            .reset_index(drop=True)
        )

    def _request_json(self, path: str, params: dict[str, Any] | None = None) -> Any:
        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.session.get(f"{self.base_url}{path}", params=params, timeout=self.timeout)
                response.raise_for_status()
                payload = response.json()
                if payload.get("Response") == "Error":
                    raise RuntimeError(str(payload.get("Message", "CryptoCompare error")))
                return payload
            except (requests.RequestException, ValueError, RuntimeError) as exc:
                last_error = exc
                logger.warning("CryptoCompare request failed on attempt %s/%s: %s", attempt, self.max_retries, exc)
                if attempt < self.max_retries:
                    sleep(0.5 * attempt)
        raise RuntimeError("CryptoCompare request failed") from last_error
