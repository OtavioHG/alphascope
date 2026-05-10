from __future__ import annotations

import logging
from datetime import datetime

from alphascope.domain.trading_schemas import PaperTrade, Position, RiskConfig
from alphascope.infrastructure.repositories.portfolio_repository import PortfolioRepository
from alphascope.infrastructure.repositories.trade_repository import TradeRepository
from alphascope.trading.portfolio import Portfolio
from alphascope.utils.time import ensure_utc

logger = logging.getLogger("alphascope.trading")


class PaperBroker:
    def __init__(
        self,
        portfolio: Portfolio | None = None,
        trade_repository: TradeRepository | None = None,
        portfolio_repository: PortfolioRepository | None = None,
        risk_config: RiskConfig | None = None,
        fee_rate: float = 0.001,
        slippage_rate: float = 0.0005,
    ):
        self.portfolio = portfolio or Portfolio()
        self.trade_repository = trade_repository or TradeRepository()
        self.portfolio_repository = portfolio_repository or PortfolioRepository()
        self.risk_config = risk_config or RiskConfig()
        self.fee_rate = fee_rate
        self.slippage_rate = slippage_rate
        self.restore_state()

    def calculate_position_size(self, price: float) -> float:
        capital_to_risk = self.portfolio.cash_balance * self.risk_config.max_risk_per_trade
        if price <= 0 or capital_to_risk <= 0:
            return 0.0
        return capital_to_risk / price

    def open_position(
        self,
        symbol: str,
        entry_price: float,
        timestamp: datetime,
        stop_loss_pct: float | None = None,
        take_profit_pct: float | None = None,
    ) -> dict:
        if len(self.portfolio.positions) >= self.risk_config.max_open_positions:
            raise ValueError("Maximum number of open positions reached")
        if symbol in self.portfolio.positions:
            raise ValueError(f"Position already open for {symbol}")

        execution_price = entry_price * (1.0 + self.slippage_rate)
        quantity = self.calculate_position_size(execution_price)
        if quantity <= 0:
            raise ValueError("Calculated position size is zero")

        gross_cost = quantity * execution_price
        entry_fee = gross_cost * self.fee_rate
        total_cost = gross_cost + entry_fee

        stop_loss = execution_price * (1.0 - (stop_loss_pct or self.risk_config.stop_loss_pct))
        take_profit = None
        active_take_profit = take_profit_pct if take_profit_pct is not None else self.risk_config.take_profit_pct
        if active_take_profit is not None:
            take_profit = execution_price * (1.0 + active_take_profit)

        position = Position(
            symbol=symbol,
            quantity=quantity,
            entry_price=execution_price,
            entry_fee=entry_fee,
            opened_at=ensure_utc(timestamp) or timestamp,
            stop_loss_price=stop_loss,
            take_profit_price=take_profit,
        )
        self.portfolio.open_position(position, total_cost)
        self.trade_repository.append_trade(
            PaperTrade(
                trade_id=f"{symbol}-{int(timestamp.timestamp())}-OPEN",
                symbol=symbol,
                side="LONG",
                entry_price=execution_price,
                exit_price=None,
                quantity=quantity,
                pnl=0.0,
                timestamp=timestamp,
                status="OPEN",
            ).to_dict()
        )
        self._persist_state({})
        logger.info("Opened paper position for %s at %.4f", symbol, execution_price)
        return position.to_dict()

    def close_position(
        self,
        symbol: str,
        exit_price: float,
        timestamp: datetime,
        status: str = "CLOSED",
    ) -> dict:
        if symbol not in self.portfolio.positions:
            raise ValueError(f"No open position for {symbol}")

        execution_price = exit_price * (1.0 - self.slippage_rate)
        position = self.portfolio.positions[symbol]
        exit_fee = (position.quantity * execution_price) * self.fee_rate
        trade = self.portfolio.close_position(
            symbol=symbol,
            exit_price=execution_price,
            exit_fee=exit_fee,
            timestamp=ensure_utc(timestamp) or timestamp,
            status=status,
        )
        trade_payload = trade.to_dict()
        self.trade_repository.append_trade(trade_payload)
        self._persist_state({})
        logger.info("Closed paper position for %s at %.4f with pnl %.4f", symbol, execution_price, trade.pnl)
        return trade_payload

    def evaluate_open_positions(
        self,
        market_prices: dict[str, float],
        timestamp: datetime,
    ) -> list[dict]:
        closed_trades: list[dict] = []
        for symbol, position in list(self.portfolio.positions.items()):
            current_price = market_prices.get(symbol)
            if current_price is None:
                continue
            if current_price <= position.stop_loss_price:
                closed_trades.append(self.close_position(symbol, current_price, timestamp, status="STOP_LOSS"))
            elif position.take_profit_price is not None and current_price >= position.take_profit_price:
                closed_trades.append(self.close_position(symbol, current_price, timestamp, status="TAKE_PROFIT"))
        if market_prices:
            self._persist_state(market_prices)
        return closed_trades

    def _persist_state(self, market_prices: dict[str, float]) -> None:
        snapshot = self.portfolio.snapshot(market_prices).to_dict()
        self.portfolio_repository.save_snapshot(snapshot)
        self.portfolio_repository.save_positions([position.to_dict() for position in self.portfolio.get_open_positions()])

    def restore_state(self) -> None:
        snapshot = self.portfolio_repository.load_snapshot()
        if snapshot:
            self.portfolio.cash_balance = float(snapshot.get("cash_balance", self.portfolio.cash_balance))

        positions_df = self.portfolio_repository.load_positions()
        if positions_df.empty:
            return

        self.portfolio.positions = {}
        for _, row in positions_df.iterrows():
            self.portfolio.positions[str(row["symbol"])] = Position(
                symbol=str(row["symbol"]),
                quantity=float(row["quantity"]),
                entry_price=float(row["entry_price"]),
                entry_fee=float(row["entry_fee"]),
                opened_at=ensure_utc(row["opened_at"]) or datetime.fromisoformat(str(row["opened_at"])),
                stop_loss_price=float(row["stop_loss_price"]),
                take_profit_price=float(row["take_profit_price"]) if str(row.get("take_profit_price", "")) not in {"", "nan", "None"} else None,
            )
