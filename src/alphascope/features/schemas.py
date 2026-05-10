from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class TechnicalFeatureSchema(BaseModel):
    symbol: str
    timestamp: datetime
    pct_return: float | None = None
    ma_short: float | None = None
    ma_long: float | None = None
    rsi: float | None = None
    volatility: float | None = None
    volume_avg: float | None = None
    relative_volume: float | None = None
    momentum: float | None = None
