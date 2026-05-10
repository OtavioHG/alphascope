"""Historical multi-agent backtesting."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from alphascope.agents.market_agent import MarketIntelligenceAgent
from alphascope.agents.news_agent import NewsSentimentAgent
from alphascope.agents.risk_agent import RiskManagementAgent
from alphascope.agents.memory_engine import MemoryEngine
from alphascope.agents.schemas import MultiAgentContext
from alphascope.agents.supervisor_agent import SupervisorAgent
from alphascope.backtest.metrics import compute_backtest_metrics
from alphascope.storage.repositories import StorageRepository
from alphascope.utils.time import utc_now


@dataclass(slots=True)
class _BacktestPosition:
    entry_price: float
    quantity: float
    opened_at: Any


class MultiAgentBacktestEngine:
    def __init__(self, repository: StorageRepository | None = None, *, initial_cash: float = 1000.0, fee_rate: float = 0.001) -> None:
        self.repository = repository or StorageRepository()
        self.initial_cash = initial_cash
        self.fee_rate = fee_rate
        self.market_agent = MarketIntelligenceAgent()
        self.news_agent = NewsSentimentAgent()
        self.risk_agent = RiskManagementAgent()
        self.memory_engine = MemoryEngine(_BacktestRepositoryAdapter(self.repository))
        self.supervisor = SupervisorAgent(_BacktestRepositoryAdapter(self.repository))

    def run(self, *, symbol: str, timeframe: str, limit: int = 300) -> dict[str, Any]:
        features = self.repository.get_features(symbol=symbol.upper(), interval=timeframe)
        if features.empty:
            raise ValueError(f"Nenhuma feature encontrada para {symbol} {timeframe}")
        features = features.sort_values("timestamp").tail(limit).reset_index(drop=True)
        ranking_history = self.repository.get_ranking_history(timeframe=timeframe, limit=limit * 5)
        if not ranking_history.empty and "symbol" in ranking_history.columns:
            ranking_history = ranking_history.loc[ranking_history["symbol"] == symbol.upper()].copy()
        snapshots = self.repository.get_market_snapshots(symbol=symbol.upper(), timeframe=timeframe, limit=limit * 5)

        cash = self.initial_cash
        position: _BacktestPosition | None = None
        trades: list[dict[str, Any]] = []
        equity_rows: list[dict[str, Any]] = []
        consensus_rows: list[dict[str, Any]] = []

        for row in features.itertuples(index=False):
            timestamp = getattr(row, "timestamp")
            close_price = float(getattr(row, "close"))
            ranking_row = self._nearest_row(ranking_history, timestamp)
            snapshot_row = self._nearest_row(snapshots, timestamp)
            account = {
                "total_balance": cash + ((position.quantity * close_price) if position else 0.0),
                "free_balance": cash,
                "exposure_pct": 0.0 if position is None else min(1.0, (position.quantity * close_price) / max(1.0, cash + (position.quantity * close_price))),
                "open_positions": 0 if position is None else 1,
            }
            context = MultiAgentContext(
                symbol=symbol.upper(),
                timeframe=timeframe,
                candles=[],
                features=row._asdict(),
                ranking=ranking_row,
                account=account,
                open_positions=[] if position is None else [{"symbol": symbol.upper(), "quantity": position.quantity, "entry_price": position.entry_price}],
                daily_performance={"consecutive_losses": 0, "max_drawdown": 0.0},
                market_snapshots=[snapshot_row] if snapshot_row else [],
                feature_snapshots=[],
                model_predictions=[],
                recent_consensus=[],
                recent_agent_decisions=[],
            )
            market_output = self.market_agent.analyze(context)
            news_output = self.news_agent.analyze(context)
            risk_output = self.risk_agent.analyze(context)
            memory_output = self.memory_engine.analyze(context)
            supervisor = self.supervisor.supervise(market=market_output, news=news_output, risk=risk_output, memory=memory_output)
            consensus_rows.append(
                {
                    "timestamp": timestamp,
                    "symbol": symbol.upper(),
                    "decision": supervisor.decision,
                    "final_score": supervisor.final_score,
                    "consensus": supervisor.consensus,
                }
            )

            if supervisor.decision == "BUY" and position is None and close_price > 0:
                fee = cash * self.fee_rate
                investable = cash - fee
                quantity = investable / close_price
                position = _BacktestPosition(entry_price=close_price, quantity=quantity, opened_at=timestamp)
                trades.append({"timestamp": timestamp, "symbol": symbol.upper(), "side": "BUY", "price": close_price, "quantity": quantity, "fee": fee, "realized_pnl": 0.0})
                cash = 0.0
            elif supervisor.decision == "SELL" and position is not None:
                gross = position.quantity * close_price
                fee = gross * self.fee_rate
                cash = gross - fee
                realized_pnl = cash - (position.quantity * position.entry_price)
                trades.append({"timestamp": timestamp, "symbol": symbol.upper(), "side": "SELL", "price": close_price, "quantity": position.quantity, "fee": fee, "realized_pnl": realized_pnl})
                position = None

            equity = cash + ((position.quantity * close_price) if position else 0.0)
            equity_rows.append({"timestamp": timestamp, "symbol": symbol.upper(), "signal": supervisor.decision, "equity": equity, "cash": cash, "quantity": 0.0 if position is None else position.quantity, "close": close_price})

        if position is not None and equity_rows:
            last_row = equity_rows[-1]
            close_price = float(last_row["close"])
            gross = position.quantity * close_price
            fee = gross * self.fee_rate
            cash = gross - fee
            realized_pnl = cash - (position.quantity * position.entry_price)
            trades.append({"timestamp": last_row["timestamp"], "symbol": symbol.upper(), "side": "SELL", "price": close_price, "quantity": position.quantity, "fee": fee, "realized_pnl": realized_pnl})
            last_row["equity"] = cash
            last_row["cash"] = cash
            last_row["quantity"] = 0.0

        trades_df = pd.DataFrame(trades)
        equity_df = pd.DataFrame(equity_rows)
        consensus_df = pd.DataFrame(consensus_rows)
        metrics = compute_backtest_metrics(equity_df, trades_df, self.initial_cash)
        metrics["consensus_rows"] = float(len(consensus_df))
        return {"metrics": metrics, "trades": trades_df, "equity_curve": equity_df, "consensus": consensus_df}

    @staticmethod
    def _nearest_row(frame: pd.DataFrame, timestamp: Any) -> dict[str, Any]:
        if frame.empty or "timestamp" not in frame.columns:
            return {}
        ordered = frame.sort_values("timestamp")
        candidates = ordered.loc[pd.to_datetime(ordered["timestamp"], utc=True) <= pd.to_datetime(timestamp, utc=True)]
        if candidates.empty:
            candidates = ordered.head(1)
        return candidates.iloc[-1].to_dict() if not candidates.empty else {}


class _BacktestRepositoryAdapter:
    def __init__(self, storage: StorageRepository) -> None:
        self.storage = storage

    def get_recent_consensus(self, *, symbol: str | None = None, limit: int = 100):
        frame = self.storage.get_trade_history(status="CLOSED", symbol=symbol, limit=limit)
        return frame.to_dict(orient="records") if not frame.empty else []

    def get_recent_agent_decisions(self, *, symbol: str | None = None, limit: int = 100):
        return []

    def get_dynamic_weight_multipliers(self):
        return {"nemotron": 1.0, "gpt_oss": 1.0, "minimax": 1.0, "trinity": 1.0}
