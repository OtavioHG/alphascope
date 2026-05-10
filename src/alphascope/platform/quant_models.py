from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum

from alphascope.utils.time import ensure_utc, safe_utc_diff


class MarketRegime(str, Enum):
    bull = "bull"
    bear = "bear"
    sideways = "sideways"


@dataclass(slots=True)
class SignalContext:
    symbol: str
    close: float
    rsi: float
    macd_histogram: float
    ma_fast: float
    ma_slow: float
    trend_strength: float
    relative_volume: float
    volatility: float
    momentum: float
    breakout_strength: float
    btc_aligned: bool = True
    timeframe_alignment: bool = True
    market_is_sideways: bool = False


@dataclass(slots=True)
class SignalDecision:
    symbol: str
    should_buy: bool
    regime: MarketRegime
    total_score: float
    trend_score: float
    volume_score: float
    volatility_score: float
    momentum_score: float
    blocked_reasons: list[str] = field(default_factory=list)


@dataclass(slots=True)
class PositionContext:
    symbol: str
    entry_price: float
    current_price: float
    quantity: float
    score: float
    current_rank: int
    best_alternative_score_gap: float
    momentum_score: float
    trailing_stop_price: float | None = None
    stop_loss_price: float | None = None
    opened_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    now: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    realized_partial_pct: float = 0.0

    @property
    def age(self) -> timedelta:
        return safe_utc_diff(ensure_utc(self.now), ensure_utc(self.opened_at))

    @property
    def pnl_pct(self) -> float:
        if self.entry_price <= 0:
            return 0.0
        return (self.current_price / self.entry_price) - 1.0


@dataclass(slots=True)
class ExitDecision:
    action: str
    reason: str
    quantity_pct: float = 1.0
    updated_stop_price: float | None = None


@dataclass(slots=True)
class PortfolioRiskState:
    equity: float
    free_cash: float
    daily_pnl_pct: float
    open_positions: int
    daily_trades: int
    consecutive_losses: int
    portfolio_exposure_pct: float
    symbol_exposure_pct: float
    candidate_volatility: float


@dataclass(slots=True)
class RiskDecision:
    approved: bool
    reason: str
    recommended_position_pct: float
    pause_trading: bool = False
    trigger_emergency_exit: bool = False


@dataclass(slots=True)
class OrderIntent:
    symbol: str
    side: str
    price: float
    quantity: float
    notional: float
    last_trade_minutes_ago: float | None = None
    duplicate_order_open: bool = False
    existing_position: bool = False


@dataclass(slots=True)
class ExchangeFilters:
    min_qty: float
    step_size: float
    tick_size: float
    min_notional: float


@dataclass(slots=True)
class OrderValidation:
    accepted: bool
    reason: str
    normalized_price: float
    normalized_quantity: float
