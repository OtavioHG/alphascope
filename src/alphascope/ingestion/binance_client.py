"""HTTP client for Binance public market data."""

from __future__ import annotations

from time import sleep

import pandas as pd
import requests

from alphascope.config.constants import BINANCE_ALLOWED_INTERVALS, BINANCE_KLINES_ENDPOINT, MARKET_CANDLE_COLUMNS
from alphascope.config.settings import settings
from alphascope.core.exceptions import IngestionError
from alphascope.core.logger import get_logger
from alphascope.utils.time import from_milliseconds

logger = get_logger(__name__)


class BinanceClient:
    """Minimal Binance REST client with timeout and retry handling."""

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
        return self.get_klines(symbol, interval, limit)

    def get_klines(self, symbol: str, interval: str, limit: int) -> pd.DataFrame:
        if interval not in BINANCE_ALLOWED_INTERVALS:
            raise IngestionError(f"Unsupported Binance interval: {interval}")

        params = {"symbol": symbol.upper(), "interval": interval, "limit": int(limit)}
        last_error: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.session.get(
                    f"{self.base_url}{BINANCE_KLINES_ENDPOINT}",
                    params=params,
                    timeout=self.timeout,
                )
                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, list):
                    raise IngestionError(f"Unexpected Binance payload: {payload}")
                frame = self._normalize_klines(payload, symbol=symbol.upper(), interval=interval)
                logger.info("Fetched %s candles for %s %s", len(frame), symbol.upper(), interval)
                return frame
            except (requests.RequestException, ValueError, IngestionError) as exc:
                last_error = exc
                logger.warning(
                    "Binance request failed for %s %s on attempt %s/%s: %s",
                    symbol.upper(),
                    interval,
                    attempt,
                    self.max_retries,
                    exc,
                )
                if attempt < self.max_retries:
                    sleep(0.5 * attempt)

        raise IngestionError(f"Failed to fetch Binance klines for {symbol} {interval}") from last_error

    @staticmethod
    def _normalize_klines(payload: list[list[object]], symbol: str, interval: str) -> pd.DataFrame:
        rows: list[dict[str, object]] = []
        for item in payload:
            rows.append(
                {
                    "timestamp": from_milliseconds(int(item[0])),
                    "open": float(item[1]),
                    "high": float(item[2]),
                    "low": float(item[3]),
                    "close": float(item[4]),
                    "volume": float(item[5]),
                    "symbol": symbol,
                    "interval": interval,
                }
            )
        frame = pd.DataFrame(rows, columns=MARKET_CANDLE_COLUMNS)
        if not frame.empty:
            frame = frame.sort_values("timestamp").reset_index(drop=True)
        return frame
