"""Binance external market source."""

from __future__ import annotations

from datetime import UTC, datetime

import pandas as pd

from alphascope.config.settings import settings
from alphascope.external_data.base import ExternalMarketSource
from alphascope.external_data.normalizers import canonicalize_asset_symbol, safe_float, split_binance_symbol
from alphascope.external_data.schemas import MarketAssetSnapshot


class BinanceMarketSource(ExternalMarketSource):
    """Market snapshot source backed by Binance public endpoints."""

    source_name = "binance"

    def __init__(self) -> None:
        super().__init__(base_url=settings.binance_base_url)

    def fetch_market_snapshot(self, limit: int = 250) -> pd.DataFrame:
        payload = self._request_json("/api/v3/ticker/24hr")
        timestamp = datetime.now(UTC)
        rows = []
        for item in payload[:limit]:
            base_asset, quote_asset = split_binance_symbol(str(item["symbol"]))
            snapshot = MarketAssetSnapshot(
                source=self.source_name,
                symbol=f"{base_asset}/{quote_asset}",
                base_asset=base_asset,
                quote_asset=quote_asset,
                price=safe_float(item.get("lastPrice")),
                volume_24h=safe_float(item.get("quoteVolume")),
                market_cap=None,
                rank=None,
                timestamp=timestamp,
                raw_symbol=str(item["symbol"]),
                canonical_symbol=canonicalize_asset_symbol(base_asset),
                exchange="binance",
                extra_metadata={
                    "price_change_percent": safe_float(item.get("priceChangePercent")),
                    "trade_count": item.get("count"),
                },
            )
            rows.append(snapshot.to_record())
        return pd.DataFrame(rows)

    def fetch_supported_assets(self, limit: int = 500) -> pd.DataFrame:
        payload = self._request_json("/api/v3/exchangeInfo")
        timestamp = datetime.now(UTC)
        rows = []
        for item in payload.get("symbols", [])[:limit]:
            base_asset = str(item.get("baseAsset", "")).upper()
            quote_asset = str(item.get("quoteAsset", "")).upper()
            snapshot = MarketAssetSnapshot(
                source=self.source_name,
                symbol=f"{base_asset}/{quote_asset}",
                base_asset=base_asset,
                quote_asset=quote_asset,
                price=None,
                volume_24h=None,
                market_cap=None,
                rank=None,
                timestamp=timestamp,
                raw_symbol=str(item.get("symbol", "")),
                canonical_symbol=canonicalize_asset_symbol(base_asset),
                exchange="binance",
                extra_metadata={"status": item.get("status")},
            )
            rows.append(snapshot.to_record())
        return pd.DataFrame(rows)
