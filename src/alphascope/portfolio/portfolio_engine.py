from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import pandas as pd

from alphascope.portfolio.allocation import AllocationEngine
from alphascope.portfolio.risk_management import PortfolioRiskConfig, RiskManager


@dataclass(slots=True)
class PortfolioPosition:
    symbol: str
    quantity: float
    entry_price: float
    allocation_amount: float
    opened_at: datetime

    def market_value(self, price: float) -> float:
        return self.quantity * price


class MultiAssetPortfolioEngine:
    def __init__(
        self,
        initial_equity: float = 10_000.0,
        allocation_engine: AllocationEngine | None = None,
        risk_manager: RiskManager | None = None,
    ):
        self.initial_equity = initial_equity
        self.available_capital = initial_equity
        self.positions: dict[str, PortfolioPosition] = {}
        self.realized_pnl = 0.0
        self.peak_equity = initial_equity
        self.allocation_engine = allocation_engine or AllocationEngine()
        self.risk_manager = risk_manager or RiskManager(PortfolioRiskConfig())

    def open_position(self, symbol: str, price: float, allocation_amount: float, timestamp: datetime | None = None) -> dict[str, Any]:
        timestamp = timestamp or datetime.now(UTC)
        if symbol in self.positions:
            raise ValueError(f"Position already exists for {symbol}")
        approved, reason = self.risk_manager.validate_new_position(
            allocation_amount=allocation_amount,
            total_equity=self.total_equity(),
            current_exposure=self.total_exposure(price_map={}),
            open_positions=len(self.positions),
        )
        if not approved:
            raise ValueError(reason)
        if allocation_amount > self.available_capital:
            raise ValueError("insufficient_capital")
        quantity = allocation_amount / price if price > 0 else 0.0
        position = PortfolioPosition(symbol=symbol, quantity=quantity, entry_price=price, allocation_amount=allocation_amount, opened_at=timestamp)
        self.positions[symbol] = position
        self.available_capital -= allocation_amount
        return self.snapshot(price_map={})

    def close_position(self, symbol: str, price: float) -> dict[str, Any]:
        if symbol not in self.positions:
            raise ValueError(f"No open position for {symbol}")
        position = self.positions.pop(symbol)
        proceeds = position.market_value(price)
        pnl = proceeds - position.allocation_amount
        self.available_capital += proceeds
        self.realized_pnl += pnl
        return {
            "symbol": symbol,
            "exit_price": price,
            "pnl": pnl,
        }

    def rebalance(self, candidates_df: pd.DataFrame, timestamp: datetime | None = None) -> dict[str, Any]:
        timestamp = timestamp or datetime.now(UTC)
        allocations = self.allocation_engine.allocate(candidates_df, self.available_capital)
        opened = []
        for _, row in candidates_df.iterrows():
            symbol = str(row["symbol"])
            if symbol in self.positions:
                continue
            allocation_amount = float(allocations.get(symbol, 0.0))
            if allocation_amount <= 0:
                continue
            try:
                self.open_position(symbol, float(row["close"]), allocation_amount, timestamp)
                opened.append(symbol)
            except ValueError:
                continue
        return {"opened_positions": opened, "snapshot": self.snapshot(self.current_price_map(candidates_df))}

    def current_price_map(self, market_df: pd.DataFrame) -> dict[str, float]:
        if market_df.empty:
            return {}
        latest = market_df.groupby("symbol", as_index=False).tail(1)
        return {str(row["symbol"]): float(row["close"]) for _, row in latest.iterrows()}

    def total_equity(self, price_map: dict[str, float] | None = None) -> float:
        return self.available_capital + sum(
            position.market_value((price_map or {}).get(symbol, position.entry_price))
            for symbol, position in self.positions.items()
        )

    def total_exposure(self, price_map: dict[str, float] | None = None) -> float:
        equity = self.total_equity(price_map)
        if equity <= 0:
            return 0.0
        invested = sum(position.market_value((price_map or {}).get(symbol, position.entry_price)) for symbol, position in self.positions.items())
        return invested / equity

    def portfolio_return(self, price_map: dict[str, float] | None = None) -> float:
        return (self.total_equity(price_map) / self.initial_equity) - 1.0 if self.initial_equity > 0 else 0.0

    def snapshot(self, price_map: dict[str, float] | None = None) -> dict[str, Any]:
        total_equity = self.total_equity(price_map)
        self.peak_equity = max(self.peak_equity, total_equity)
        return {
            "total_equity": total_equity,
            "available_capital": self.available_capital,
            "open_positions": len(self.positions),
            "portfolio_value": total_equity,
            "portfolio_return": self.portfolio_return(price_map),
            "portfolio_exposure": self.total_exposure(price_map),
            "realized_pnl": self.realized_pnl,
        }
