"""Execution engine for live-simulated portfolio updates."""

from __future__ import annotations

from dataclasses import dataclass

from alphascope.config.settings import settings
from alphascope.execution.order_sizing import calculate_order_sizing
from alphascope.execution.portfolio import Portfolio, Position
from alphascope.simulation.signal_dispatcher import Signal
from alphascope.utils.time import utc_now


@dataclass(slots=True)
class SimulationExecutionResult:
    """Execution summary for a batch of simulation signals."""

    trades: list[dict[str, object]]
    rejected_signals: int


class ExecutionSimulator:
    """Apply buy/sell signals to a simulated portfolio."""

    def __init__(
        self,
        *,
        fee_rate: float = settings.paper_fee_rate,
        max_positions: int = settings.paper_max_positions,
    ) -> None:
        self.fee_rate = fee_rate
        self.max_positions = max_positions

    def execute(self, signals: list[Signal], portfolio: Portfolio) -> SimulationExecutionResult:
        """Execute a batch of signals and mutate the in-memory portfolio."""
        trades: list[dict[str, object]] = []
        rejected_signals = 0

        for signal in signals:
            if signal.action == "BUY":
                trade = self._buy(portfolio, signal)
            elif signal.action == "SELL":
                trade = self._sell(portfolio, signal)
            else:
                trade = None
            if trade is None:
                rejected_signals += 1
                continue
            trades.append(trade)

        return SimulationExecutionResult(trades=trades, rejected_signals=rejected_signals)

    def mark_to_market(self, portfolio: Portfolio, latest_prices: dict[str, float]) -> None:
        """Refresh market prices for open positions."""
        for symbol, position in portfolio.positions.items():
            if symbol in latest_prices:
                position.market_price = latest_prices[symbol]

    def _buy(self, portfolio: Portfolio, signal: Signal) -> dict[str, object] | None:
        if signal.symbol in portfolio.positions or len(portfolio.positions) >= self.max_positions:
            return None
        if signal.price <= 0.0:
            return None
        sizing = calculate_order_sizing(signal.price, available_balance=portfolio.cash, symbol=signal.symbol)
        if sizing.blocked_reason:
            return None
        fee = sizing.order_value_usd * self.fee_rate
        total_cost = sizing.order_value_usd + fee
        if total_cost > portfolio.cash:
            return None
        quantity = sizing.final_quantity
        if quantity <= 0.0:
            return None

        portfolio.cash -= total_cost
        portfolio.positions[signal.symbol] = Position(
            symbol=signal.symbol,
            quantity=quantity,
            average_price=signal.price,
            market_price=signal.price,
        )
        return {
            "timestamp": utc_now(),
            "symbol": signal.symbol,
            "side": "BUY",
            "quantity": quantity,
            "price": signal.price,
            "fee": fee,
            "realized_pnl": 0.0,
            "order_value": sizing.order_value_usd,
        }

    def _sell(self, portfolio: Portfolio, signal: Signal) -> dict[str, object] | None:
        position = portfolio.positions.get(signal.symbol)
        if position is None:
            return None
        gross_value = position.quantity * signal.price
        fee = gross_value * self.fee_rate
        realized_pnl = (signal.price - position.average_price) * position.quantity - fee
        portfolio.cash += gross_value - fee
        portfolio.realized_pnl += realized_pnl
        del portfolio.positions[signal.symbol]
        return {
            "timestamp": utc_now(),
            "symbol": signal.symbol,
            "side": "SELL",
            "quantity": position.quantity,
            "price": signal.price,
            "fee": fee,
            "realized_pnl": realized_pnl,
        }
