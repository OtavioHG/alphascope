from __future__ import annotations

import pandas as pd

from alphascope.features.technical import compute_technical_features


def test_compute_technical_features_generates_required_columns_without_leakage():
    rows = 80
    candles = pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-01", periods=rows, freq="h", tz="UTC"),
            "symbol": ["BTCUSDT"] * rows,
            "interval": ["1h"] * rows,
            "open": [100 + i for i in range(rows)],
            "high": [101 + i for i in range(rows)],
            "low": [99 + i for i in range(rows)],
            "close": [100 + (i * 0.5) for i in range(rows)],
            "volume": [1000 + (i * 10) for i in range(rows)],
        }
    )

    features = compute_technical_features(
        candles=candles,
        short_window=5,
        long_window=10,
        rsi_window=14,
        volatility_window=10,
        volume_window=10,
        momentum_window=3,
    )

    assert not features.empty
    assert {
        "return_pct",
        "ma_short",
        "ma_long",
        "rsi",
        "volatility",
        "avg_volume",
        "relative_volume",
        "momentum",
        "trend_strength",
    }.issubset(features.columns)
    reference_row = features.iloc[0]
    source_index = candles.index[candles["timestamp"] == reference_row["timestamp"]][0]
    expected_ma_short = candles.iloc[source_index - 4 : source_index + 1]["close"].mean()
    assert round(reference_row["ma_short"], 10) == round(expected_ma_short, 10)
