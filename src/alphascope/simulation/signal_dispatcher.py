"""Translate ranking frames into simulated trading signals."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from alphascope.config.settings import settings


@dataclass(slots=True)
class Signal:
    """Normalized trading signal consumed by the execution simulator."""

    symbol: str
    action: str
    score: float
    price: float
    reason: str


class SignalDispatcher:
    """Create buy/sell/hold intentions from ranking and current portfolio state."""

    def __init__(
        self,
        *,
        buy_threshold: float = settings.rank_buy_threshold,
        sell_threshold: float = settings.rank_sell_threshold,
    ) -> None:
        self.buy_threshold = buy_threshold
        self.sell_threshold = sell_threshold

    def dispatch(
        self,
        ranking: pd.DataFrame,
        latest_prices: dict[str, float],
        open_positions: set[str],
    ) -> list[Signal]:
        """Convert ranking rows into actionable simulation signals."""
        if ranking.empty:
            return []

        signals: list[Signal] = []
        for row in ranking.itertuples(index=False):
            symbol = str(row.symbol).upper()
            price = latest_prices.get(symbol)
            if price is None:
                continue
            score = float(getattr(row, "score", 0.0))
            if score >= self.buy_threshold and symbol not in open_positions:
                signals.append(Signal(symbol=symbol, action="BUY", score=score, price=price, reason="ranking_buy_threshold"))
            elif score <= self.sell_threshold and symbol in open_positions:
                signals.append(Signal(symbol=symbol, action="SELL", score=score, price=price, reason="ranking_sell_threshold"))
        return signals
