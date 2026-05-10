from __future__ import annotations

import pandas as pd

from alphascope.backtest.engine import BacktestEngine
from alphascope.backtest.strategy import ProbabilityThresholdStrategy
from alphascope.models.ranking import build_asset_ranking


def test_build_asset_ranking_orders_by_final_score() -> None:
    predictions = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(["2024-01-01", "2024-01-01", "2024-01-01"]),
            "symbol": ["BTCUSDT", "ETHUSDT", "SOLUSDT"],
            "predicted_label": [1, 1, 1],
            "predicted_probability": [0.82, 0.78, 0.74],
            "confidence_score": [0.64, 0.56, 0.48],
            "volatility": [0.02, 0.04, 0.08],
            "relative_volume": [1.8, 1.2, 0.8],
        }
    )

    ranking = build_asset_ranking(predictions)
    assert ranking.iloc[0]["symbol"] == "BTCUSDT"
    assert ranking["score_final"].is_monotonic_decreasing


def test_backtest_engine_executes_buy_and_sell_cycle() -> None:
    predictions = pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-01", periods=5, freq="h"),
            "symbol": ["BTCUSDT"] * 5,
            "open": [100, 101, 104, 103, 102],
            "close": [100, 102, 105, 103, 101],
            "predicted_probability": [0.8, 0.78, 0.4, 0.3, 0.2],
        }
    )
    signals = ProbabilityThresholdStrategy().generate_signals(predictions)
    result = BacktestEngine(initial_cash=1000.0, fee_rate=0.0, slippage_rate=0.0).run(signals, model_name="test_model")

    assert len(result["trades"]) == 2
    assert result["trades"].iloc[0]["side"] == "BUY"
    assert result["trades"].iloc[1]["side"] == "SELL"
    assert result["summary"]["number_of_trades"] == 1
