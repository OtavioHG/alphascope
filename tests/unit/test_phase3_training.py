from __future__ import annotations

import shutil
from pathlib import Path

import pandas as pd

from alphascope.domain.model_schemas import TargetConfig, TrainingConfig
from alphascope.models.dataset import Phase3DatasetBuilder
from alphascope.models.evaluate import compute_classification_metrics
from alphascope.models.predict import load_model_artifact, predict_from_dataframe
from alphascope.models.train import Phase3Trainer


def _training_dataset() -> pd.DataFrame:
    timestamps = pd.date_range("2024-01-01", periods=120, freq="h")
    pattern = [0.03, -0.02, 0.025, -0.015, 0.018, -0.01]
    closes = [100.0]
    for index in range(1, len(timestamps)):
        closes.append(closes[-1] * (1.0 + pattern[index % len(pattern)]))

    df = pd.DataFrame(
        {
            "timestamp": timestamps,
            "symbol": ["BTCUSDT"] * len(timestamps),
            "open": closes,
            "high": [value * 1.01 for value in closes],
            "low": [value * 0.99 for value in closes],
            "close": closes,
            "volume": [100 + (index % 7) * 10 for index in range(len(timestamps))],
        }
    )
    df["rsi"] = [40 + (index % 20) for index in range(len(df))]
    df["macd"] = df["close"].pct_change().fillna(0).rolling(3, min_periods=1).mean()
    df["macd_signal"] = df["macd"].rolling(2, min_periods=1).mean()
    df["bb_upper"] = df["close"] * 1.02
    df["bb_lower"] = df["close"] * 0.98
    df["sma_20"] = df["close"].rolling(5, min_periods=1).mean()
    df["sma_50"] = df["close"].rolling(10, min_periods=1).mean()
    df["pct_return"] = df["close"].pct_change().fillna(0)
    df["volatility"] = df["pct_return"].rolling(5, min_periods=1).std().fillna(0.01)
    df["relative_volume"] = df["volume"] / df["volume"].rolling(5, min_periods=1).mean()
    df["sentiment_score"] = [0.2 if value > 0 else -0.1 for value in df["pct_return"]]
    df["news_count_window"] = [index % 3 for index in range(len(df))]
    df["avg_sentiment_window"] = df["sentiment_score"]
    df["top_topic"] = ["btc" if index % 2 == 0 else "macro" for index in range(len(df))]
    return df


def test_compute_classification_metrics_returns_expected_fields() -> None:
    metrics = compute_classification_metrics(
        y_true=[0, 1, 1, 0],
        y_pred=[0, 1, 0, 0],
        y_prob=[0.1, 0.9, 0.4, 0.2],
    )

    assert 0.0 <= metrics.accuracy <= 1.0
    assert metrics.confusion_matrix == [[2, 0], [1, 1]]


def test_phase3_trainer_produces_model_artifact() -> None:
    base_dir = Path("data/processed/test_phase3_training")
    if base_dir.exists():
        shutil.rmtree(base_dir)
    base_dir.mkdir(parents=True, exist_ok=True)

    dataset_path = base_dir / "dataset.csv"
    _training_dataset().to_csv(dataset_path, index=False)

    config = TrainingConfig(
        artifact_dir=base_dir / "models",
        report_dir=base_dir / "reports",
        target=TargetConfig(future_horizon=1, return_threshold=0.01),
    )
    result = Phase3Trainer(config=config).train(dataset_path=str(dataset_path), symbol="BTCUSDT", interval="1h")

    artifact = load_model_artifact(result["artifact_path"])
    prepared = Phase3DatasetBuilder(feature_columns=artifact["feature_columns"]).prepare_dataset(pd.read_csv(dataset_path))
    predictions = predict_from_dataframe(artifact, prepared.head(10), latest_only=False)

    assert result["artifact_path"].exists()
    assert result["report_path"].exists()
    assert "predicted_probability" in predictions.columns
    assert artifact["metadata"]["model_name"] in {"logistic_regression", "random_forest", "gradient_boosting"}
