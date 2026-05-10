from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass(slots=True)
class RiskConfig:
    max_risk_per_trade: float = 0.02
    max_open_positions: int = 5
    stop_loss_pct: float = 0.05
    take_profit_pct: float | None = None


@dataclass(slots=True)
class Position:
    symbol: str
    quantity: float
    entry_price: float
    entry_fee: float
    opened_at: datetime
    stop_loss_price: float
    take_profit_price: float | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["opened_at"] = self.opened_at.isoformat()
        return payload


@dataclass(slots=True)
class PaperTrade:
    trade_id: str
    symbol: str
    side: str
    entry_price: float
    exit_price: float | None
    quantity: float
    pnl: float
    timestamp: datetime
    status: str

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["timestamp"] = self.timestamp.isoformat()
        return payload


@dataclass(slots=True)
class PortfolioSnapshot:
    cash_balance: float
    equity: float
    open_positions: int
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ExecutionDecision:
    symbol: str
    action: str
    probability: float
    price: float
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
