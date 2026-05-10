"""Paper trading engine."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

import pandas as pd

from alphascope.config.settings import settings
from alphascope.core.logger import get_logger
from alphascope.execution.order_sizing import calculate_order_sizing
from alphascope.execution.portfolio import Portfolio, Position
from alphascope.storage.repositories import StorageRepository
from alphascope.utils.time import utc_now

logger = get_logger(__name__)


class PaperTrader:
    """Simulate portfolio decisions from the latest asset ranking."""

    def __init__(self, repository: StorageRepository | None = None, initial_cash: float | None = None) -> None:
        self.repository = repository or StorageRepository()
        self.portfolio = self._load_portfolio(initial_cash)
        self.fee_rate = settings.paper_fee_rate
        self.max_positions = settings.paper_max_positions

    def execute_multi_agent_plan(
        self,
        *,
        symbol: str,
        side: str,
        price: float,
        final_score: float,
        execution_plan: dict[str, Any],
        supervisor: dict[str, Any],
        market_output: dict[str, Any] | None = None,
        news_output: dict[str, Any] | None = None,
        risk_output: dict[str, Any] | None = None,
        memory_output: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        ranking_context = {
            "score": final_score,
            "confidence_score": float(supervisor.get("final_score", final_score) or final_score),
            "ml_probability": float(market_output.get("score", 0.0) if market_output else 0.0),
            "heuristic_score": float(market_output.get("score", final_score) if market_output else final_score),
            "news_score": float(news_output.get("score", 0.0) if news_output else 0.0),
            "volatility": float((market_output or {}).get("metadata", {}).get("volatility", 0.0)),
            "relative_volume": float((market_output or {}).get("metadata", {}).get("relative_volume", 0.0)),
            "source": "multi_agent",
            "multi_agent_execution": execution_plan,
            "multi_agent_supervisor": supervisor,
            "multi_agent_risk": risk_output or {},
            "multi_agent_memory": memory_output or {},
        }
        try:
            if side.upper() == "BUY":
                trade = self.buy(symbol.upper(), price, ranking_context=ranking_context)
                return {"status": "opened" if trade else "blocked", "trade": trade, "mode": "paper"}
            trade = self.sell(symbol.upper(), price, ranking_context=ranking_context)
            return {"status": "closed" if trade else "ignored", "trade": trade, "mode": "paper"}
        except Exception as exc:
            logger.exception("paper_multi_agent_execution_failed symbol=%s", symbol.upper())
            return {"status": "blocked", "reason": str(exc), "mode": "paper", "symbol": symbol.upper()}

    def run_cycle(self, ranking: pd.DataFrame, latest_prices: dict[str, float]) -> dict[str, object]:
        trades: list[dict[str, object]] = []
        ranking_map = {
            str(record["symbol"]).upper(): record
            for record in ranking.to_dict(orient="records")
            if str(record.get("symbol", "")).strip()
        }
        for row in ranking.itertuples(index=False):
            price = latest_prices.get(row.symbol)
            if price is None:
                continue
            if row.score >= settings.rank_buy_threshold:
                trade = self.buy(row.symbol, price, ranking_context=ranking_map.get(str(row.symbol).upper(), {}))
                if trade:
                    trades.append(trade)
            elif row.score <= settings.rank_sell_threshold:
                trade = self.sell(row.symbol, price, ranking_context=ranking_map.get(str(row.symbol).upper(), {}))
                if trade:
                    trades.append(trade)

        for symbol, position in self.portfolio.positions.items():
            if symbol in latest_prices:
                position.market_price = latest_prices[symbol]
                self.repository.update_open_trade_history_metrics(symbol, latest_prices[symbol])

        snapshot = {
            "timestamp": utc_now(),
            "cash": self.portfolio.cash,
            "equity": self.portfolio.equity(),
            "realized_pnl": self.portfolio.realized_pnl,
            "unrealized_pnl": self.portfolio.unrealized_pnl(),
            "positions_json": {
                symbol: asdict(position)
                for symbol, position in self.portfolio.positions.items()
            },
        }
        self.repository.save_trades(trades)
        self.repository.save_snapshot(snapshot)
        logger.info("Paper trading cycle completed with %s trades", len(trades))
        return {"trades": trades, "snapshot": snapshot}

    def _load_portfolio(self, initial_cash: float | None) -> Portfolio:
        snapshot = self.repository.get_latest_snapshot()
        if snapshot is None:
            return Portfolio(cash=initial_cash or settings.paper_initial_cash)

        positions = {
            symbol: Position(**position_data)
            for symbol, position_data in dict(snapshot["positions_json"]).items()
        }
        return Portfolio(
            cash=float(snapshot["cash"]),
            realized_pnl=float(snapshot["realized_pnl"]),
            positions=positions,
        )

    def buy(self, symbol: str, price: float, *, ranking_context: dict[str, object] | None = None) -> dict[str, object] | None:
        if symbol in self.portfolio.positions or len(self.portfolio.positions) >= self.max_positions:
            logger.warning("trade_blocked symbol=%s reason=max_open_trades_reached", symbol)
            return None
        if self.portfolio.cash < settings.min_balance_required:
            logger.warning("trade_blocked symbol=%s reason=min_balance_required", symbol)
            return None
        sizing = calculate_order_sizing(price, available_balance=self.portfolio.cash, symbol=symbol)
        if sizing.blocked_reason:
            logger.warning("trade_blocked symbol=%s reason=%s", symbol, sizing.blocked_reason)
            return None
        fee = sizing.order_value_usd * self.fee_rate
        total_cost = sizing.order_value_usd + fee
        if total_cost > self.portfolio.cash:
            logger.warning("trade_blocked symbol=%s reason=insufficient_balance", symbol)
            return None
        quantity = sizing.final_quantity
        if quantity <= 0.0:
            return None
        logger.info(
            "trade_attempt symbol=%s price=%s calculated_order_value=%.2f calculated_quantity=%.8f min_notional_required=%.2f final_quantity=%.8f",
            symbol,
            price,
            sizing.order_value_usd,
            sizing.calculated_quantity,
            sizing.min_notional_required,
            sizing.final_quantity,
        )
        self.portfolio.cash -= total_cost
        self.portfolio.positions[symbol] = Position(
            symbol=symbol,
            quantity=quantity,
            average_price=price,
            market_price=price,
        )
        context = ranking_context or {}
        trade_id = f"paper_{symbol}_{int(utc_now().timestamp())}"
        self.repository.open_trade_history(
            {
                "trade_id": trade_id,
                "order_id": trade_id,
                "symbol": symbol,
                "timeframe": settings.default_interval,
                "side": "BUY",
                "mode": "paper",
                "status": "OPEN",
                "entry_time": utc_now(),
                "entry_price": price,
                "quantity": quantity,
                "order_size_usdt": sizing.order_value_usd,
                "fees_paid": fee,
                "ranking_score": float(context.get("score", 0.0)),
                "confidence_score": float(context.get("confidence_score", max(context.get("score", 0.0), context.get("ml_probability", 0.0)))),
                "ml_score": float(context.get("ml_probability", 0.0)),
                "heuristic_score": float(context.get("heuristic_score", context.get("score", 0.0))),
                "news_score": float(context.get("news_score", 0.0)),
                "volatility": float(context.get("volatility", 0.0)),
                "volume_ratio": float(context.get("relative_volume", 0.0)),
                "trend_direction": "up" if float(context.get("score", 0.0)) >= settings.rank_buy_threshold else "sideways",
                "reason_opened": str(context.get("source", "ranking_threshold")),
                "notes_json": context,
                "created_at": utc_now(),
                "updated_at": utc_now(),
            }
        )
        logger.info(
            "trade_executed symbol=%s order_side=BUY order_value=%.2f final_quantity=%.8f price=%s",
            symbol,
            sizing.order_value_usd,
            quantity,
            price,
        )
        return {
            "timestamp": utc_now(),
            "symbol": symbol,
            "side": "BUY",
            "quantity": quantity,
            "price": price,
            "fee": fee,
            "realized_pnl": 0.0,
            "order_value": sizing.order_value_usd,
        }

    def sell(self, symbol: str, price: float, *, ranking_context: dict[str, object] | None = None) -> dict[str, object] | None:
        position = self.portfolio.positions.get(symbol)
        if position is None:
            return None
        gross_value = position.quantity * price
        fee = gross_value * self.fee_rate
        realized_pnl = (price - position.average_price) * position.quantity - fee
        self.portfolio.cash += gross_value - fee
        self.portfolio.realized_pnl += realized_pnl
        del self.portfolio.positions[symbol]
        self.repository.close_latest_open_trade(
            symbol=symbol,
            reason_closed=str((ranking_context or {}).get("source", "ranking_sell_threshold")),
            exit_price=price,
            fees_paid=fee,
            notes_json=ranking_context or {},
        )
        logger.info(
            "trade_executed symbol=%s order_side=SELL order_value=%.2f final_quantity=%.8f price=%s",
            symbol,
            gross_value,
            position.quantity,
            price,
        )
        return {
            "timestamp": utc_now(),
            "symbol": symbol,
            "side": "SELL",
            "quantity": position.quantity,
            "price": price,
            "fee": fee,
            "realized_pnl": realized_pnl,
        }
