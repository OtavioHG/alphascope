from __future__ import annotations

import logging
from datetime import datetime

import pandas as pd

from alphascope.domain.trading_schemas import ExecutionDecision
from alphascope.trading.paper_broker import PaperBroker
from alphascope.utils.time import ensure_utc

logger = logging.getLogger("alphascope.trading")


class ExecutionEngine:
    def __init__(
        self,
        broker: PaperBroker,
        buy_threshold: float = 0.75,
        sell_threshold: float = 0.35,
    ):
        self.broker = broker
        self.buy_threshold = buy_threshold
        self.sell_threshold = sell_threshold

    def process_predictions(self, predictions_df: pd.DataFrame) -> dict[str, list[dict]]:
        if predictions_df.empty:
            return {"decisions": [], "opened": [], "closed": []}

        ordered = predictions_df.sort_values(["timestamp", "symbol"]).copy()
        market_prices = {
            row["symbol"]: float(row["close"])
            for _, row in ordered.iterrows()
            if "close" in ordered.columns
        }
        last_timestamp = ensure_utc(ordered["timestamp"].max())
        if last_timestamp is None:
            return {"decisions": [], "opened": [], "closed": []}
        closed = self.broker.evaluate_open_positions(market_prices, last_timestamp)

        opened: list[dict] = []
        decisions: list[dict] = []

        latest_rows = ordered.groupby("symbol", as_index=False).tail(1)
        for _, row in latest_rows.iterrows():
            symbol = str(row["symbol"])
            probability = float(row["predicted_probability"])
            price = float(row["close"]) if "close" in row else 0.0
            timestamp = ensure_utc(row["timestamp"])
            if timestamp is None:
                continue

            if probability >= self.buy_threshold and symbol not in self.broker.portfolio.positions:
                decision = ExecutionDecision(symbol=symbol, action="BUY", probability=probability, price=price, reason="threshold_buy")
                decisions.append(decision.to_dict())
                try:
                    opened.append(self.broker.open_position(symbol, price, timestamp))
                except ValueError as exc:
                    logger.warning("Skipping buy for %s: %s", symbol, exc)
            elif probability <= self.sell_threshold and symbol in self.broker.portfolio.positions:
                decision = ExecutionDecision(symbol=symbol, action="SELL", probability=probability, price=price, reason="threshold_sell")
                decisions.append(decision.to_dict())
                closed.append(self.broker.close_position(symbol, price, timestamp, status="SIGNAL_EXIT"))
            else:
                action = "HOLD"
                if symbol in self.broker.portfolio.positions:
                    reason = "position_held"
                else:
                    reason = "threshold_not_met"
                decisions.append(
                    ExecutionDecision(symbol=symbol, action=action, probability=probability, price=price, reason=reason).to_dict()
                )

        return {"decisions": decisions, "opened": opened, "closed": closed}
