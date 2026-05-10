"""Backtest metrics."""

from __future__ import annotations

import numpy as np
import pandas as pd


def compute_backtest_metrics(
    equity_curve: pd.DataFrame,
    trades: pd.DataFrame,
    initial_cash: float,
) -> dict[str, float]:
    if equity_curve.empty:
        return {
            "cumulative_return": 0.0,
            "win_rate": 0.0,
            "max_drawdown": 0.0,
            "profit_factor": 0.0,
            "trade_count": 0.0,
        }

    realized = trades.loc[trades["side"] == "SELL", "realized_pnl"] if not trades.empty else pd.Series(dtype=float)
    gross_profit = realized[realized > 0].sum()
    gross_loss = -realized[realized < 0].sum()
    equity = equity_curve["equity"].astype(float)
    drawdown = (equity / equity.cummax()) - 1.0

    return {
        "cumulative_return": float((equity.iloc[-1] / initial_cash) - 1.0),
        "win_rate": float((realized > 0).mean()) if not realized.empty else 0.0,
        "max_drawdown": float(drawdown.min()),
        "profit_factor": float(gross_profit / gross_loss) if gross_loss > 0 else float(np.inf if gross_profit > 0 else 0.0),
        "trade_count": float(len(realized)),
    }
