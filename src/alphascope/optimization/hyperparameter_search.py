from __future__ import annotations

import itertools
import random
from pathlib import Path
from typing import Any

import pandas as pd

from alphascope.models.dataset import Phase3DatasetBuilder
from alphascope.models.evaluate import compute_classification_metrics
from alphascope.models.registry import build_model_registry
from alphascope.models.targets import build_binary_target
from alphascope.domain.model_schemas import TargetConfig


class HyperparameterSearch:
    def __init__(self, output_dir: str | Path = "data/processed/optimization", seed: int = 42):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.seed = seed

    def search(
        self,
        dataset_path: str,
        model_name: str,
        param_grid: dict[str, list[Any]],
        method: str = "grid",
        max_trials: int | None = None,
    ) -> dict[str, Any]:
        builder = Phase3DatasetBuilder()
        dataset = builder.load_dataset(dataset_path)
        prepared = builder.prepare_dataset(dataset)
        labeled = build_binary_target(prepared, TargetConfig())
        feature_columns = builder.infer_feature_columns(labeled)
        train_df, validation_df, _ = builder.temporal_split(labeled)

        all_combinations = [
            dict(zip(param_grid.keys(), values))
            for values in itertools.product(*param_grid.values())
        ]
        if method == "random" and max_trials is not None:
            random.Random(self.seed).shuffle(all_combinations)
            all_combinations = all_combinations[:max_trials]

        results = []
        for params in all_combinations:
            pipeline = build_model_registry(seed=self.seed)[model_name]
            pipeline.set_params(**params)
            pipeline.fit(train_df[feature_columns], train_df["target"].astype(int))
            probabilities = pipeline.predict_proba(validation_df[feature_columns])[:, 1]
            predictions = (probabilities >= 0.5).astype(int)
            metrics = compute_classification_metrics(validation_df["target"].astype(int), predictions, probabilities)
            results.append({"params": params, "f1_score": metrics.f1_score, "roc_auc": metrics.roc_auc or 0.0})

        frame = pd.DataFrame(results)
        path = self.output_dir / f"hyperparameter_search_{model_name}.csv"
        frame.to_csv(path, index=False)
        best = max(results, key=lambda row: row["f1_score"]) if results else None
        return {"results": frame, "path": path, "best": best}
