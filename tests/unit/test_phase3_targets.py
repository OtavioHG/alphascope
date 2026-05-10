from __future__ import annotations

import pandas as pd

from alphascope.domain.model_schemas import TargetConfig
from alphascope.models.dataset import Phase3DatasetBuilder
from alphascope.models.targets import build_binary_target


def _sample_dataset() -> pd.DataFrame:
    timestamps = pd.date_range("2024-01-01", periods=8, freq="h")
    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "symbol": ["BTCUSDT"] * 8,
            "close": [100, 103, 101, 105, 104, 108, 106, 110],
            "open": [100, 102, 102, 103, 104, 106, 107, 108],
            "high": [101, 104, 103, 106, 105, 109, 108, 111],
            "low": [99, 101, 100, 102, 103, 105, 105, 107],
            "volume": [10, 12, 11, 15, 14, 18, 16, 20],
            "rsi": [45, 55, 48, 62, 52, 68, 58, 70],
            "macd": [0.1, 0.3, 0.2, 0.5, 0.4, 0.8, 0.6, 1.0],
            "macd_signal": [0.05, 0.2, 0.15, 0.35, 0.3, 0.55, 0.45, 0.7],
            "bb_upper": [102, 105, 104, 107, 106, 110, 109, 112],
            "bb_lower": [98, 99, 98, 100, 101, 103, 104, 105],
            "sma_20": [100, 101, 101, 102, 103, 104, 105, 106],
            "sma_50": [99, 100, 100, 101, 102, 103, 104, 105],
            "pct_return": [0.0, 0.03, -0.02, 0.04, -0.01, 0.038, -0.018, 0.037],
            "volatility": [0.02] * 8,
            "relative_volume": [1.0, 1.2, 1.1, 1.5, 1.3, 1.6, 1.4, 1.7],
            "sentiment_score": [0.1, 0.3, 0.0, 0.4, 0.2, 0.5, 0.1, 0.6],
            "news_count_window": [1, 1, 0, 2, 1, 2, 1, 3],
            "avg_sentiment_window": [0.1, 0.3, 0.0, 0.4, 0.2, 0.5, 0.1, 0.6],
            "top_topic": ["btc", "btc", "macro", "btc", "macro", "btc", "macro", "btc"],
        }
    )


def test_build_binary_target_respects_future_horizon() -> None:
    dataset = _sample_dataset()
    labeled = build_binary_target(
        dataset,
        TargetConfig(future_horizon=2, return_threshold=0.015),
    )

    assert len(labeled) == len(dataset) - 2
    assert round(float(labeled.loc[0, "future_return"]), 6) == 0.01
    assert int(labeled.loc[1, "target"]) == 1


def test_remove_leakage_columns_excludes_future_fields() -> None:
    builder = Phase3DatasetBuilder()
    prepared = builder.prepare_dataset(_sample_dataset())
    labeled = build_binary_target(prepared)
    safe = builder.remove_leakage_columns(labeled)

    assert "future_close" not in safe.columns
    assert "future_return" not in safe.columns
    assert "target" not in safe.columns


def test_temporal_split_preserves_order() -> None:
    builder = Phase3DatasetBuilder()
    prepared = builder.prepare_dataset(_sample_dataset())
    train_df, validation_df, test_df = builder.temporal_split(prepared)

    assert train_df["timestamp"].max() < validation_df["timestamp"].min()
    assert validation_df["timestamp"].max() < test_df["timestamp"].min()
