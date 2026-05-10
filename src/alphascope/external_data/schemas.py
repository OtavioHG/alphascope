"""Schemas for normalized external market data."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True)
class MarketAssetSnapshot:
    """Unified snapshot for a crypto asset across external data providers."""

    source: str
    symbol: str
    base_asset: str
    quote_asset: str
    price: float | None
    volume_24h: float | None
    market_cap: float | None
    rank: int | None
    timestamp: datetime
    raw_symbol: str
    canonical_symbol: str
    exchange: str | None = None
    extra_metadata: dict[str, Any] = field(default_factory=dict)

    def to_record(self) -> dict[str, Any]:
        """Convert the snapshot to a plain record suitable for pandas."""
        payload = asdict(self)
        payload["timestamp"] = self.timestamp.astimezone(UTC)
        return payload


@dataclass(frozen=True)
class SourceHealthStatus:
    """Healthcheck status for an external market source."""

    source: str
    available: bool
    checked_at: datetime
    detail: str | None = None
