from __future__ import annotations

import pandas as pd

from alphascope.backtest.engine import BacktestEngine


def test_backtest_engine_generates_metrics_and_trades():
    frame = pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-01", periods=5, freq="h", tz="UTC"),
            "symbol": ["BTCUSDT"] * 5,
            "open": [100.0, 101.0, 103.0, 104.0, 106.0],
            "close": [100.0, 102.0, 104.0, 105.0, 107.0],
            "score": [0.7, 0.75, 0.55, 0.35, 0.3],
            "signal": ["BUY", "HOLD", "HOLD", "SELL", "HOLD"],
        }
    )

    result = BacktestEngine(initial_cash=1000.0, fee_rate=0.001).run(frame)

    assert "metrics" in result
    assert result["metrics"]["trade_count"] >= 1
    assert len(result["trades"]) == 2
    assert "cumulative_return" in result["metrics"]
