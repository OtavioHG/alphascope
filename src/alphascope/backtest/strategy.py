"""Simple score-driven backtest strategy."""

from __future__ import annotations

import pandas as pd


class ThresholdStrategy:
    """Emit BUY and SELL signals from ranking score thresholds."""

    def __init__(self, buy_threshold: float, sell_threshold: float) -> None:
        self.buy_threshold = buy_threshold
        self.sell_threshold = sell_threshold

    def generate_signals(self, frame: pd.DataFrame) -> pd.DataFrame:
        dataset = frame.sort_values("timestamp").reset_index(drop=True).copy()
        signal = []
        in_position = False
        for row in dataset.itertuples(index=False):
            if not in_position and row.score >= self.buy_threshold:
                signal.append("BUY")
                in_position = True
            elif in_position and row.score <= self.sell_threshold:
                signal.append("SELL")
                in_position = False
            else:
                signal.append("HOLD")
        dataset["signal"] = signal
        return dataset


class ProbabilityThresholdStrategy(ThresholdStrategy):
    """Backward-compatible alias for older optimization and phase tests."""
