"""Portfolio state for paper trading."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Position:
    symbol: str
    quantity: float
    average_price: float
    market_price: float

    @property
    def market_value(self) -> float:
        return self.quantity * self.market_price

    @property
    def unrealized_pnl(self) -> float:
        return (self.market_price - self.average_price) * self.quantity


@dataclass
class Portfolio:
    cash: float
    realized_pnl: float = 0.0
    positions: dict[str, Position] = field(default_factory=dict)

    def equity(self) -> float:
        return self.cash + sum(position.market_value for position in self.positions.values())

    def unrealized_pnl(self) -> float:
        return sum(position.unrealized_pnl for position in self.positions.values())
