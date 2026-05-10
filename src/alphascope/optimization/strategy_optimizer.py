from __future__ import annotations

import itertools
import random
from pathlib import Path
from typing import Any

import pandas as pd

from alphascope.backtest.engine import BacktestEngine
from alphascope.backtest.strategy import ProbabilityThresholdStrategy
from alphascope.domain.model_schemas import TargetConfig, TrainingConfig
from alphascope.models.dataset import Phase3DatasetBuilder
from alphascope.models.predict import load_model_artifact, predict_from_dataframe
from alphascope.models.train import Phase3Trainer


class StrategyOptimizer:
    def __init__(self, output_dir: str | Path = "data/processed/optimization", seed: int = 42):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.seed = seed

    def optimize(
        self,
        dataset_path: str,
        symbol: str | None = None,
        interval: str | None = None,
        horizon_values: list[int] | None = None,
        threshold_values: list[float] | None = None,
        buy_thresholds: list[float] | None = None,
        sell_thresholds: list[float] | None = None,
        method: str = "grid",
        max_trials: int | None = None,
    ) -> dict[str, Any]:
        horizon_values = horizon_values or [4]
        threshold_values = threshold_values or [0.015]
        buy_thresholds = buy_thresholds or [0.75]
        sell_thresholds = sell_thresholds or [0.35]

        combinations = list(itertools.product(horizon_values, threshold_values, buy_thresholds, sell_thresholds))
        if method == "random" and max_trials is not None:
            random.Random(self.seed).shuffle(combinations)
            combinations = combinations[:max_trials]

        results = []
        builder = Phase3DatasetBuilder()
        dataset = builder.load_dataset(dataset_path)
        prepared = builder.prepare_dataset(dataset, symbol=symbol, interval=interval)

        for horizon, threshold, buy_threshold, sell_threshold in combinations:
            trainer = Phase3Trainer(
                config=TrainingConfig(
                    seed=self.seed,
                    target=TargetConfig(future_horizon=horizon, return_threshold=threshold),
                    artifact_dir=self.output_dir / "models",
                    report_dir=self.output_dir / "reports",
                )
            )
            train_result = trainer.train(dataset_path=dataset_path, symbol=symbol, interval=interval)
            artifact = load_model_artifact(train_result["artifact_path"])
            predictions = predict_from_dataframe(artifact, prepared, latest_only=False)
            signals = ProbabilityThresholdStrategy(buy_threshold=buy_threshold, sell_threshold=sell_threshold).generate_signals(predictions)
            backtest = BacktestEngine().run(signals, model_name=artifact["metadata"]["model_name"])
            summary = backtest["summary"]
            results.append(
                {
                    "horizon": horizon,
                    "return_threshold": threshold,
                    "buy_threshold": buy_threshold,
                    "sell_threshold": sell_threshold,
                    "sharpe_ratio": summary["sharpe_ratio"],
                    "total_return": summary["total_return"],
                    "max_drawdown": summary["max_drawdown"],
                }
            )

        frame = pd.DataFrame(results).sort_values("sharpe_ratio", ascending=False).reset_index(drop=True)
        path = self.output_dir / "strategy_optimization.csv"
        frame.to_csv(path, index=False)
        return {"results": frame, "path": path, "best": frame.iloc[0].to_dict() if not frame.empty else None}
