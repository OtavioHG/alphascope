from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

import pandas as pd

from alphascope.domain.trading_schemas import RiskConfig
from alphascope.infrastructure.repositories.portfolio_repository import PortfolioRepository
from alphascope.infrastructure.repositories.trade_repository import TradeRepository
from alphascope.trading.execution_engine import ExecutionEngine
from alphascope.trading.paper_broker import PaperBroker
from alphascope.trading.portfolio import Portfolio


def test_portfolio_open_and_close_updates_cash() -> None:
    base_dir = Path("data/processed/test_phase4_trading/trades_a")
    if base_dir.exists():
        shutil.rmtree(base_dir)

    portfolio = Portfolio(initial_cash=1000.0)
    broker = PaperBroker(
        portfolio=portfolio,
        trade_repository=TradeRepository(base_dir),
        portfolio_repository=PortfolioRepository(base_dir),
        risk_config=RiskConfig(max_risk_per_trade=0.1, max_open_positions=3, stop_loss_pct=0.05),
        fee_rate=0.0,
        slippage_rate=0.0,
    )

    broker.open_position("BTCUSDT", 100.0, datetime(2024, 1, 1, 0, 0, 0))
    assert len(portfolio.get_open_positions()) == 1
    assert round(portfolio.cash_balance, 2) == 900.0

    trade = broker.close_position("BTCUSDT", 110.0, datetime(2024, 1, 1, 1, 0, 0))
    assert trade["pnl"] == 10.0
    assert round(portfolio.cash_balance, 2) == 1010.0


def test_execution_engine_generates_buy_and_sell_actions() -> None:
    base_dir = Path("data/processed/test_phase4_trading/engine")
    if base_dir.exists():
        shutil.rmtree(base_dir)

    broker = PaperBroker(
        portfolio=Portfolio(initial_cash=1000.0),
        trade_repository=TradeRepository(base_dir),
        portfolio_repository=PortfolioRepository(base_dir),
        risk_config=RiskConfig(max_risk_per_trade=0.1, max_open_positions=2, stop_loss_pct=0.05),
        fee_rate=0.0,
        slippage_rate=0.0,
    )
    engine = ExecutionEngine(broker=broker)

    buy_frame = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(["2024-01-01 00:00:00"]),
            "symbol": ["BTCUSDT"],
            "close": [100.0],
            "predicted_probability": [0.82],
        }
    )
    buy_result = engine.process_predictions(buy_frame)
    assert len(buy_result["opened"]) == 1
    assert buy_result["decisions"][0]["action"] == "BUY"

    sell_frame = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(["2024-01-01 01:00:00"]),
            "symbol": ["BTCUSDT"],
            "close": [96.0],
            "predicted_probability": [0.20],
        }
    )
    sell_result = engine.process_predictions(sell_frame)
    assert len(sell_result["closed"]) == 1
    assert sell_result["decisions"][0]["action"] == "SELL"
