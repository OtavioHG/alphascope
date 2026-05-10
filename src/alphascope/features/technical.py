"""Technical indicator calculations."""

from __future__ import annotations

import numpy as np
import pandas as pd


def compute_technical_features(
    candles: pd.DataFrame,
    short_window: int,
    long_window: int,
    rsi_window: int,
    volatility_window: int,
    volume_window: int,
    momentum_window: int,
) -> pd.DataFrame:
    """Build lag-safe technical features from historical candles."""
    if candles.empty:
        return pd.DataFrame()

    dataset = candles.sort_values(["symbol", "timestamp"]).reset_index(drop=True).copy()
    grouped = dataset.groupby("symbol", group_keys=False)

    dataset["return_pct"] = grouped["close"].pct_change()
    dataset["ma_short"] = grouped["close"].transform(lambda s: s.rolling(window=short_window, min_periods=short_window).mean())
    dataset["ma_long"] = grouped["close"].transform(lambda s: s.rolling(window=long_window, min_periods=long_window).mean())
    dataset["volatility"] = grouped["return_pct"].transform(
        lambda s: s.rolling(window=volatility_window, min_periods=volatility_window).std(ddof=0)
    )
    dataset["avg_volume"] = grouped["volume"].transform(
        lambda s: s.rolling(window=volume_window, min_periods=volume_window).mean()
    )
    dataset["relative_volume"] = dataset["volume"] / dataset["avg_volume"]
    dataset["momentum"] = grouped["close"].transform(lambda s: s / s.shift(momentum_window) - 1.0)
    dataset["trend_strength"] = (dataset["ma_short"] / dataset["ma_long"]) - 1.0
    dataset["rsi"] = grouped["close"].transform(lambda s: _compute_rsi(s, window=rsi_window))

    columns = [
        "timestamp",
        "symbol",
        "interval",
        "close",
        "return_pct",
        "ma_short",
        "ma_long",
        "rsi",
        "volatility",
        "avg_volume",
        "relative_volume",
        "momentum",
        "trend_strength",
    ]
    return dataset.loc[:, columns].dropna().reset_index(drop=True)


def _compute_rsi(close: pd.Series, window: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.rolling(window=window, min_periods=window).mean()
    avg_loss = loss.rolling(window=window, min_periods=window).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi.fillna(50.0)
