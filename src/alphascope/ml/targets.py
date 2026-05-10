"""Target generation functions for market ML."""

from __future__ import annotations

import pandas as pd


def future_return_target(close: pd.Series, horizon_bars: int) -> pd.Series:
    """Compute the future return over a fixed horizon."""
    future_close = close.shift(-horizon_bars)
    return (future_close / close) - 1.0


def up_move_target(close: pd.Series, horizon_bars: int, threshold_pct: float) -> pd.Series:
    """Binary target indicating whether price rises above threshold over the horizon."""
    future_return = future_return_target(close=close, horizon_bars=horizon_bars)
    return (future_return >= threshold_pct).astype(float)


def binary_breakout_target(high: pd.Series, close: pd.Series, horizon_bars: int, threshold_pct: float) -> pd.Series:
    """Binary target indicating whether future high breaks out above the threshold."""
    future_high = high.shift(-horizon_bars).rolling(window=horizon_bars, min_periods=1).max()
    breakout_return = (future_high / close) - 1.0
    return (breakout_return >= threshold_pct).astype(float)
