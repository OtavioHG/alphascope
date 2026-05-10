from __future__ import annotations

from datetime import datetime

from alphascope.domain.trading_schemas import PaperTrade, PortfolioSnapshot, Position


class Portfolio:
    def __init__(self, initial_cash: float = 10_000.0):
        self.initial_cash = initial_cash
        self.cash_balance = initial_cash
        self.positions: dict[str, Position] = {}
        self.trade_history: list[PaperTrade] = []

    def open_position(self, position: Position, total_cost: float) -> None:
        if position.symbol in self.positions:
            raise ValueError(f"Position already open for {position.symbol}")
        if total_cost > self.cash_balance:
            raise ValueError("Insufficient cash to open position")
        self.cash_balance -= total_cost
        self.positions[position.symbol] = position

    def close_position(
        self,
        symbol: str,
        exit_price: float,
        exit_fee: float,
        timestamp: datetime,
        status: str = "CLOSED",
    ) -> PaperTrade:
        if symbol not in self.positions:
            raise ValueError(f"No open position for {symbol}")

        position = self.positions.pop(symbol)
        gross_value = position.quantity * exit_price
        net_value = gross_value - exit_fee
        self.cash_balance += net_value
        pnl = net_value - ((position.quantity * position.entry_price) + position.entry_fee)
        trade = PaperTrade(
            trade_id=f"{symbol}-{int(timestamp.timestamp())}",
            symbol=symbol,
            side="LONG",
            entry_price=position.entry_price,
            exit_price=exit_price,
            quantity=position.quantity,
            pnl=pnl,
            timestamp=timestamp,
            status=status,
        )
        self.trade_history.append(trade)
        return trade

    def get_portfolio_value(self, market_prices: dict[str, float] | None = None) -> float:
        prices = market_prices or {}
        position_value = 0.0
        for symbol, position in self.positions.items():
            mark_price = prices.get(symbol, position.entry_price)
            position_value += position.quantity * mark_price
        return self.cash_balance + position_value

    def get_open_positions(self) -> list[Position]:
        return list(self.positions.values())

    def snapshot(self, market_prices: dict[str, float] | None = None) -> PortfolioSnapshot:
        return PortfolioSnapshot(
            cash_balance=self.cash_balance,
            equity=self.get_portfolio_value(market_prices),
            open_positions=len(self.positions),
        )
