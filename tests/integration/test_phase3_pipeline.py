from __future__ import annotations

import shutil
from pathlib import Path

import pandas as pd

from alphascope.backtest.engine import BacktestEngine
from alphascope.backtest.strategy import ProbabilityThresholdStrategy
from alphascope.domain.model_schemas import TargetConfig, TrainingConfig
from alphascope.models.dataset import Phase3DatasetBuilder
from alphascope.models.predict import load_model_artifact, predict_from_dataframe
from alphascope.models.ranking import build_asset_ranking
from alphascope.models.targets import build_binary_target
from alphascope.models.train import Phase3Trainer


def _multi_asset_dataset() -> pd.DataFrame:
    timestamps = pd.date_range("2024-01-01", periods=80, freq="h")
    rows = []
    for symbol, bias in (("BTCUSDT", 0.02), ("ETHUSDT", 0.01)):
        close = 100.0
        for index, timestamp in enumerate(timestamps):
            delta = bias if index % 2 == 0 else -0.012
            close *= 1.0 + delta
            rows.append(
                {
                    "timestamp": timestamp,
                    "symbol": symbol,
                    "open": close,
                    "high": close * 1.01,
                    "low": close * 0.99,
                    "close": close,
                    "volume": 100 + index,
                    "rsi": 45 + (index % 15),
                    "macd": delta,
                    "macd_signal": delta / 2,
                    "bb_upper": close * 1.03,
                    "bb_lower": close * 0.97,
                    "sma_20": close * 0.99,
                    "sma_50": close * 0.98,
                    "pct_return": delta,
                    "volatility": abs(delta),
                    "relative_volume": 1.0 + ((index % 5) / 10),
                    "sentiment_score": 0.3 if delta > 0 else -0.1,
                    "news_count_window": index % 4,
                    "avg_sentiment_window": 0.3 if delta > 0 else -0.1,
                    "top_topic": "btc" if symbol == "BTCUSDT" else "eth",
                }
            )
    return pd.DataFrame(rows)


def test_phase3_pipeline_end_to_end() -> None:
    base_dir = Path("data/processed/test_phase3_pipeline")
    if base_dir.exists():
        shutil.rmtree(base_dir)
    base_dir.mkdir(parents=True, exist_ok=True)

    dataset_path = base_dir / "dataset.csv"
    dataset = _multi_asset_dataset()
    dataset.to_csv(dataset_path, index=False)

    trainer = Phase3Trainer(
        config=TrainingConfig(
            artifact_dir=base_dir / "models",
            report_dir=base_dir / "reports",
            target=TargetConfig(future_horizon=1, return_threshold=0.005),
        )
    )
    train_result = trainer.train(str(dataset_path), interval="1h")
    artifact = load_model_artifact(train_result["artifact_path"])

    builder = Phase3DatasetBuilder(feature_columns=artifact["feature_columns"])
    prepared = builder.prepare_dataset(dataset)
    predictions = predict_from_dataframe(artifact, prepared, latest_only=True)
    ranking = build_asset_ranking(predictions)
    full_predictions = predict_from_dataframe(
        artifact,
        prepared.loc[prepared["symbol"] == "BTCUSDT"],
        latest_only=False,
    )
    signals = ProbabilityThresholdStrategy().generate_signals(full_predictions)
    backtest = BacktestEngine(initial_cash=5000.0, fee_rate=0.0, slippage_rate=0.0).run(
        signals,
        model_name=artifact["metadata"]["model_name"],
    )
    labeled = build_binary_target(dataset, TargetConfig(future_horizon=1, return_threshold=0.005))

    assert not predictions.empty
    assert not ranking.empty
    assert backtest["summary"]["final_equity"] > 0
    assert len(labeled) == len(dataset) - 2
