from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from alphascope.models.dataset import Phase3DatasetBuilder
from alphascope.models.evaluate import compute_classification_metrics
from alphascope.models.registry import build_model_registry
from alphascope.models.targets import build_binary_target
from alphascope.domain.model_schemas import TargetConfig


class WalkForwardValidator:
    def __init__(self, output_dir: str | Path = "data/processed/optimization", seed: int = 42):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.seed = seed
        self.builder = Phase3DatasetBuilder()

    def run(
        self,
        dataset_path: str,
        model_name: str = "logistic_regression",
        train_size: int = 200,
        test_size: int = 50,
        step_size: int = 50,
        horizon: int = 4,
        threshold: float = 0.015,
    ) -> dict[str, Any]:
        dataset = self.builder.load_dataset(dataset_path)
        prepared = self.builder.prepare_dataset(dataset)
        labeled = build_binary_target(prepared, TargetConfig(future_horizon=horizon, return_threshold=threshold))
        feature_columns = self.builder.infer_feature_columns(labeled)

        results = []
        registry = build_model_registry(seed=self.seed)
        for index, (train_df, test_df) in enumerate(self.builder.walk_forward_splits(labeled, train_size, test_size, step_size), start=1):
            pipeline = registry[model_name]
            pipeline.fit(train_df[feature_columns], train_df["target"].astype(int))
            probabilities = pipeline.predict_proba(test_df[feature_columns])[:, 1]
            predictions = (probabilities >= 0.5).astype(int)
            metrics = compute_classification_metrics(test_df["target"].astype(int), predictions, probabilities)
            results.append(
                {
                    "window": index,
                    "train_start": str(train_df["timestamp"].min()),
                    "train_end": str(train_df["timestamp"].max()),
                    "test_start": str(test_df["timestamp"].min()),
                    "test_end": str(test_df["timestamp"].max()),
                    "f1_score": metrics.f1_score,
                    "precision": metrics.precision,
                    "recall": metrics.recall,
                    "roc_auc": metrics.roc_auc,
                }
            )

        frame = pd.DataFrame(results)
        path = self.output_dir / f"walk_forward_{model_name}.csv"
        frame.to_csv(path, index=False)
        return {"results": frame, "path": path}
