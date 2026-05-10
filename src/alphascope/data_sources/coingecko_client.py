"""CoinGecko market data client."""

from __future__ import annotations

from time import sleep
from typing import Any

import pandas as pd
import requests

from alphascope.config.settings import settings
from alphascope.core.logger import get_logger
from alphascope.external_data.normalizers import canonicalize_asset_symbol, safe_float, safe_int

logger = get_logger(__name__)


class CoinGeckoDataClient:
    """Client for CoinGecko demo/public market endpoints."""

    def __init__(
        self,
        base_url: str | None = None,
        timeout: int | None = None,
        max_retries: int | None = None,
        session: requests.Session | None = None,
    ) -> None:
        self.base_url = (base_url or settings.coingecko_base_url).rstrip("/")
        self.timeout = timeout or settings.request_timeout
        self.max_retries = max_retries or settings.request_retries
        self.session = session or requests.Session()
        if settings.enable_coingecko and not settings.coingecko_using_api_key:
            logger.info(
                "CoinGecko running without API key. Public endpoints remain available, but rate limits may be lower."
            )

    def fetch_market_metrics(self, limit: int = 250) -> pd.DataFrame:
        """Fetch market cap, rank and metadata for coins."""
        per_page = min(limit, settings.external_market_page_size)
        pages = max(1, min(settings.external_market_max_pages, (limit - 1) // per_page + 1))
        rows: list[dict[str, object]] = []
        for page in range(1, pages + 1):
            payload = self._request_json(
                "/api/v3/coins/markets",
                params={
                    "vs_currency": "usd",
                    "order": "market_cap_desc",
                    "per_page": per_page,
                    "page": page,
                    "sparkline": "false",
                },
            )
            for item in payload:
                symbol = str(item.get("symbol", "")).upper()
                canonical_symbol = canonicalize_asset_symbol(symbol=symbol, name=str(item.get("name", "")))
                rows.append(
                    {
                        "canonical_symbol": canonical_symbol,
                        "market_cap": safe_float(item.get("market_cap")),
                        "market_rank": safe_int(item.get("market_cap_rank")),
                        "circulating_supply": safe_float(item.get("circulating_supply")),
                        "global_volume": safe_float(item.get("total_volume")),
                        "name": item.get("name"),
                        "source": "coingecko",
                    }
                )
                if len(rows) >= limit:
                    break
            if len(rows) >= limit:
                break
        return pd.DataFrame(rows)

    def fetch_asset_metadata(self, limit: int = 500) -> pd.DataFrame:
        """Fetch broad asset metadata from the coin list endpoint."""
        payload = self._request_json("/api/v3/coins/list", params={"include_platform": "false"})
        rows = []
        for item in payload[:limit]:
            canonical_symbol = canonicalize_asset_symbol(
                symbol=str(item.get("symbol", "")),
                name=str(item.get("name", "")),
            )
            rows.append(
                {
                    "canonical_symbol": canonical_symbol,
                    "name": item.get("name"),
                    "coingecko_id": item.get("id"),
                    "source": "coingecko",
                }
            )
        return pd.DataFrame(rows)

    def _request_json(self, path: str, params: dict[str, Any] | None = None) -> Any:
        headers: dict[str, str] = {}
        if settings.coingecko_api_key:
            headers["x-cg-demo-api-key"] = settings.coingecko_api_key

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
                logger.warning("CoinGecko request failed on attempt %s/%s: %s", attempt, self.max_retries, exc)
                if attempt < self.max_retries:
                    sleep(0.5 * attempt)
        raise RuntimeError("CoinGecko request failed") from last_error
