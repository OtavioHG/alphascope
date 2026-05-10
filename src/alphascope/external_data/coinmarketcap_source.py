"""CoinMarketCap external market source."""

from __future__ import annotations

from datetime import UTC, datetime

import pandas as pd

from alphascope.config.settings import settings
from alphascope.core.logger import get_logger
from alphascope.external_data.base import ExternalMarketSource
from alphascope.external_data.normalizers import canonicalize_asset_symbol, safe_float, safe_int
from alphascope.external_data.schemas import MarketAssetSnapshot

logger = get_logger(__name__)


class CoinMarketCapMarketSource(ExternalMarketSource):
    """Market snapshot source backed by the CoinMarketCap free API."""

    source_name = "coinmarketcap"

    def __init__(self) -> None:
        super().__init__(base_url=settings.coinmarketcap_base_url)

    def fetch_market_snapshot(self, limit: int = 250) -> pd.DataFrame:
        if not settings.coinmarketcap_api_enabled:
            logger.warning("Skipping CoinMarketCap market snapshot because the source is disabled or the API key is missing.")
            return pd.DataFrame()

        payload = self._request_json(
            "/v1/cryptocurrency/listings/latest",
            params={"start": 1, "limit": min(limit, 5000), "convert": "USD"},
            headers={"X-CMC_PRO_API_KEY": str(settings.coinmarketcap_api_key)},
        )
        timestamp = datetime.now(UTC)
        rows = []
        for item in payload.get("data", [])[:limit]:
            symbol = str(item.get("symbol", "")).upper()
            quote = item.get("quote", {}).get("USD", {})
            canonical_symbol = canonicalize_asset_symbol(symbol=symbol, name=str(item.get("name", "")))
            snapshot = MarketAssetSnapshot(
                source=self.source_name,
                symbol=canonical_symbol,
                base_asset=canonical_symbol,
                quote_asset="USD",
                price=safe_float(quote.get("price")),
                volume_24h=safe_float(quote.get("volume_24h")),
                market_cap=safe_float(quote.get("market_cap")),
                rank=safe_int(item.get("cmc_rank")),
                timestamp=timestamp,
                raw_symbol=str(item.get("slug", symbol)),
                canonical_symbol=canonical_symbol,
                exchange=None,
                extra_metadata={
                    "name": item.get("name"),
                    "circulating_supply": safe_float(item.get("circulating_supply")),
                    "percent_change_24h": safe_float(quote.get("percent_change_24h")),
                },
            )
            rows.append(snapshot.to_record())
        return pd.DataFrame(rows)

    def fetch_supported_assets(self, limit: int = 500) -> pd.DataFrame:
        return self.fetch_market_snapshot(limit=limit).loc[
            :,
            [
                "source",
                "symbol",
                "base_asset",
                "quote_asset",
                "price",
                "volume_24h",
                "market_cap",
                "rank",
                "timestamp",
                "raw_symbol",
                "canonical_symbol",
                "exchange",
                "extra_metadata",
            ],
        ]
