"""Backtest engine for AlphaScope V1."""

from __future__ import annotations

import pandas as pd

from alphascope.backtest.metrics import compute_backtest_metrics
from alphascope.core.exceptions import BacktestError


class BacktestEngine:
    """Run a single-asset long-only backtest using next-bar execution."""

    def __init__(self, initial_cash: float, fee_rate: float) -> None:
        self.initial_cash = initial_cash
        self.fee_rate = fee_rate

    def run(self, signal_frame: pd.DataFrame) -> dict[str, pd.DataFrame | dict[str, float]]:
        if signal_frame.empty:
            raise BacktestError("Signal frame is empty")

        dataset = signal_frame.sort_values("timestamp").reset_index(drop=True).copy()
        dataset["next_open"] = dataset["open"].shift(-1)

        cash = self.initial_cash
        quantity = 0.0
        entry_cost = 0.0
        trades: list[dict[str, object]] = []
        equity_rows: list[dict[str, object]] = []

        for row in dataset.itertuples(index=False):
            execution_price = float(row.next_open) if pd.notna(row.next_open) else float(row.close)
            close_price = float(row.close)

            if row.signal == "BUY" and quantity == 0.0:
                trade_fee = cash * self.fee_rate
                investable_cash = cash - trade_fee
                quantity = investable_cash / execution_price if execution_price > 0 else 0.0
                entry_cost = cash
                cash = 0.0
                trades.append(
                    {
                        "timestamp": row.timestamp,
                        "symbol": row.symbol,
                        "side": "BUY",
                        "price": execution_price,
                        "quantity": quantity,
                        "fee": trade_fee,
                        "realized_pnl": 0.0,
                    }
                )
            elif row.signal == "SELL" and quantity > 0.0:
                gross_value = quantity * execution_price
                trade_fee = gross_value * self.fee_rate
                cash = gross_value - trade_fee
                realized_pnl = cash - entry_cost
                trades.append(
                    {
                        "timestamp": row.timestamp,
                        "symbol": row.symbol,
                        "side": "SELL",
                        "price": execution_price,
                        "quantity": quantity,
                        "fee": trade_fee,
                        "realized_pnl": realized_pnl,
                    }
                )
                quantity = 0.0
                entry_cost = 0.0

            equity_rows.append(
                {
                    "timestamp": row.timestamp,
                    "symbol": row.symbol,
                    "signal": row.signal,
                    "equity": cash + (quantity * close_price),
                    "cash": cash,
                    "quantity": quantity,
                    "close": close_price,
                }
            )

        if quantity > 0.0:
            last_row = dataset.iloc[-1]
            gross_value = quantity * float(last_row["close"])
            trade_fee = gross_value * self.fee_rate
            cash = gross_value - trade_fee
            trades.append(
                {
                    "timestamp": last_row["timestamp"],
                    "symbol": last_row["symbol"],
                    "side": "SELL",
                    "price": float(last_row["close"]),
                    "quantity": quantity,
                    "fee": trade_fee,
                    "realized_pnl": cash - entry_cost,
                }
            )
            equity_rows[-1]["equity"] = cash
            equity_rows[-1]["cash"] = cash
            equity_rows[-1]["quantity"] = 0.0

        trades_df = pd.DataFrame(trades)
        equity_df = pd.DataFrame(equity_rows)
        metrics = compute_backtest_metrics(equity_df, trades_df, self.initial_cash)
        return {"metrics": metrics, "trades": trades_df, "equity_curve": equity_df}
