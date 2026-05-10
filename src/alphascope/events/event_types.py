from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

MARKET_DATA_UPDATED = "MarketDataUpdated"
FEATURES_COMPUTED = "FeaturesComputed"
MODEL_PREDICTION_READY = "ModelPredictionReady"
RANKING_UPDATED = "RankingUpdated"
TRADE_EXECUTED = "TradeExecuted"
PORTFOLIO_UPDATED = "PortfolioUpdated"


@dataclass(slots=True)
class Event:
    name: str
    payload: dict[str, Any]
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
