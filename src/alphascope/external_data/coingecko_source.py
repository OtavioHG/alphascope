"""CoinGecko external market source."""

from __future__ import annotations

from datetime import UTC, datetime

import pandas as pd

from alphascope.config.settings import settings
from alphascope.external_data.base import ExternalMarketSource
from alphascope.external_data.normalizers import canonicalize_asset_symbol, safe_float, safe_int
from alphascope.external_data.schemas import MarketAssetSnapshot


class CoinGeckoMarketSource(ExternalMarketSource):
    """Market snapshot source backed by the CoinGecko demo API."""

    source_name = "coingecko"

    def __init__(self) -> None:
        super().__init__(base_url=settings.coingecko_base_url)

    def fetch_market_snapshot(self, limit: int = 250) -> pd.DataFrame:
        per_page = min(limit, settings.external_market_page_size)
        pages = max(1, min(settings.external_market_max_pages, (limit - 1) // per_page + 1))
        timestamp = datetime.now(UTC)
        rows: list[dict[str, object]] = []
        headers = self._build_headers()

        for page in range(1, pages + 1):
            payload = self._request_json(
                "/api/v3/coins/markets",
                params={
                    "vs_currency": "usd",
                    "order": "market_cap_desc",
                    "per_page": per_page,
                    "page": page,
                    "sparkline": "false",
                    "price_change_percentage": "24h",
                },
                headers=headers,
            )
            for item in payload:
                symbol = str(item.get("symbol", "")).upper()
                canonical_symbol = canonicalize_asset_symbol(symbol=symbol, name=str(item.get("name", "")))
                snapshot = MarketAssetSnapshot(
                    source=self.source_name,
                    symbol=canonical_symbol,
                    base_asset=canonical_symbol,
                    quote_asset="USD",
                    price=safe_float(item.get("current_price")),
                    volume_24h=safe_float(item.get("total_volume")),
                    market_cap=safe_float(item.get("market_cap")),
                    rank=safe_int(item.get("market_cap_rank")),
                    timestamp=timestamp,
                    raw_symbol=str(item.get("id", symbol)),
                    canonical_symbol=canonical_symbol,
                    exchange=None,
                    extra_metadata={
                        "name": item.get("name"),
                        "image": item.get("image"),
                        "price_change_percentage_24h": safe_float(item.get("price_change_percentage_24h")),
                    },
                )
                rows.append(snapshot.to_record())
                if len(rows) >= limit:
                    break
            if len(rows) >= limit:
                break
        return pd.DataFrame(rows)

    def fetch_supported_assets(self, limit: int = 500) -> pd.DataFrame:
        payload = self._request_json("/api/v3/coins/list", params={"include_platform": "false"}, headers=self._build_headers())
        timestamp = datetime.now(UTC)
        rows = []
        for item in payload[:limit]:
            canonical_symbol = canonicalize_asset_symbol(symbol=str(item.get("symbol", "")), name=str(item.get("name", "")))
            snapshot = MarketAssetSnapshot(
                source=self.source_name,
                symbol=canonical_symbol,
                base_asset=canonical_symbol,
                quote_asset="USD",
                price=None,
                volume_24h=None,
                market_cap=None,
                rank=None,
                timestamp=timestamp,
                raw_symbol=str(item.get("id", "")),
                canonical_symbol=canonical_symbol,
                exchange=None,
                extra_metadata={"name": item.get("name")},
            )
            rows.append(snapshot.to_record())
        return pd.DataFrame(rows)

    def _build_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {}
        if settings.coingecko_api_key:
            headers["x-cg-demo-api-key"] = settings.coingecko_api_key
        return headers
