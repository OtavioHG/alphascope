"""CoinMarketCap market data client."""

from __future__ import annotations

from time import sleep
from typing import Any

import pandas as pd
import requests

from alphascope.config.settings import settings
from alphascope.core.logger import get_logger
from alphascope.external_data.normalizers import canonicalize_asset_symbol, safe_float, safe_int

logger = get_logger(__name__)


class CoinMarketCapDataClient:
    """Client for CoinMarketCap free API listings and quotes."""

    def __init__(
        self,
        base_url: str | None = None,
        timeout: int | None = None,
        max_retries: int | None = None,
        session: requests.Session | None = None,
    ) -> None:
        self.base_url = (base_url or settings.coinmarketcap_base_url).rstrip("/")
        self.timeout = timeout or settings.request_timeout
        self.max_retries = max_retries or settings.request_retries
        self.session = session or requests.Session()
        if settings.enable_coinmarketcap and not settings.coinmarketcap_api_enabled:
            logger.warning(
                "CoinMarketCap requested but COINMARKETCAP_API_KEY is empty. Source will stay disabled."
            )

    def fetch_market_metrics(self, limit: int = 250) -> pd.DataFrame:
        """Fetch latest quotes, rank and market cap from CoinMarketCap."""
        if not settings.coinmarketcap_api_enabled:
            logger.warning("Skipping CoinMarketCap fetch because the source is disabled or the API key is missing.")
            return pd.DataFrame()
        payload = self._request_json(
            "/v1/cryptocurrency/listings/latest",
            params={"start": 1, "limit": min(limit, 5000), "convert": "USD"},
        )
        rows = []
        for item in payload.get("data", [])[:limit]:
            quote = item.get("quote", {}).get("USD", {})
            canonical_symbol = canonicalize_asset_symbol(
                symbol=str(item.get("symbol", "")),
                name=str(item.get("name", "")),
            )
            rows.append(
                {
                    "canonical_symbol": canonical_symbol,
                    "market_cap_cmc": safe_float(quote.get("market_cap")),
                    "market_rank_cmc": safe_int(item.get("cmc_rank")),
                    "volume_24h_cmc": safe_float(quote.get("volume_24h")),
                    "price_usd_cmc": safe_float(quote.get("price")),
                    "name": item.get("name"),
                    "source": "coinmarketcap",
                }
            )
        return pd.DataFrame(rows)

    def _request_json(self, path: str, params: dict[str, Any] | None = None) -> Any:
        if not settings.coinmarketcap_api_key:
            raise RuntimeError("CoinMarketCap source is unavailable because COINMARKETCAP_API_KEY is empty.")
        headers = {"X-CMC_PRO_API_KEY": str(settings.coinmarketcap_api_key)}
        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.session.get(
                    f"{self.base_url}{path}",
                    params=params,
                    headers=headers,
                    timeout=self.timeout,
                )
                response.raise_for_status()
                return response.json()
            except (requests.RequestException, ValueError) as exc:
                last_error = exc
                logger.warning("CoinMarketCap request failed on attempt %s/%s: %s", attempt, self.max_retries, exc)
                if attempt < self.max_retries:
                    sleep(0.5 * attempt)
        raise RuntimeError("CoinMarketCap request failed") from last_error
