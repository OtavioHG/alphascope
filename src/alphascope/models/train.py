from __future__ import annotations

import logging
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import joblib
import pandas as pd

from alphascope.domain.model_schemas import ModelArtifactMetadata, TrainingConfig
from alphascope.infrastructure.repositories.model import ModelRunRepository
from alphascope.models.dataset import Phase3DatasetBuilder, split_summary
from alphascope.models.evaluate import compute_classification_metrics, feature_importance_frame, model_selection_score, save_feature_report
from alphascope.models.registry import build_model_registry
from alphascope.models.targets import build_binary_target

logger = logging.getLogger(__name__)


class Phase3Trainer:
    def __init__(self, config: TrainingConfig | None = None):
        self.config = config or TrainingConfig()
        self.dataset_builder = Phase3DatasetBuilder()
        self.model_repo = ModelRunRepository()

    def build_labeled_dataset(
        self,
        dataset_path: str,
        symbol: str | None = None,
        interval: str | None = None,
        start: str | None = None,
        end: str | None = None,
    ) -> tuple[pd.DataFrame, list[str]]:
        dataset = self.dataset_builder.load_dataset(dataset_path)
        prepared = self.dataset_builder.prepare_dataset(dataset, symbol=symbol, interval=interval, start=start, end=end)
        feature_columns = self.dataset_builder.infer_feature_columns(prepared)
        labeled = build_binary_target(prepared, self.config.target)
        return labeled.dropna(subset=[self.config.target.target_column]).reset_index(drop=True), feature_columns

    def train(
        self,
        dataset_path: str,
        symbol: str | None = None,
        interval: str | None = None,
        start: str | None = None,
        end: str | None = None,
    ) -> dict[str, Any]:
        artifact_dir = Path(self.config.artifact_dir)
        artifact_dir.mkdir(parents=True, exist_ok=True)

        labeled_df, feature_columns = self.build_labeled_dataset(dataset_path, symbol=symbol, interval=interval, start=start, end=end)
        if labeled_df.empty:
            raise ValueError("No labeled rows available for training")

        train_df, validation_df, test_df = self.dataset_builder.temporal_split(labeled_df, self.config.split)
        target_column = self.config.target.target_column

        X_train = train_df[feature_columns]
        y_train = train_df[target_column].astype(int)
        X_val = validation_df[feature_columns]
        y_val = validation_df[target_column].astype(int)

        candidates = build_model_registry(seed=self.config.seed, class_weight=self.config.positive_class_weight)
        candidates = {name: pipeline for name, pipeline in candidates.items() if name in self.config.model_names}

        candidate_results: list[dict[str, Any]] = []
        for model_name, pipeline in candidates.items():
            logger.info("Training candidate model %s", model_name)
            fitted = pipeline.fit(X_train, y_train)
            val_probabilities = fitted.predict_proba(X_val)[:, 1]
            val_predictions = (val_probabilities >= 0.5).astype(int)
            validation_metrics = compute_classification_metrics(y_val, val_predictions, val_probabilities)
            candidate_results.append(
                {
                    "model_name": model_name,
                    "validation_metrics": validation_metrics,
                    "selection_score": model_selection_score(validation_metrics),
                }
            )

        best_result = max(candidate_results, key=lambda item: item["selection_score"])
        best_model_name = best_result["model_name"]

        train_validation_df = pd.concat([train_df, validation_df], ignore_index=True)
        X_train_validation = train_validation_df[feature_columns]
        y_train_validation = train_validation_df[target_column].astype(int)
        X_test = test_df[feature_columns]
        y_test = test_df[target_column].astype(int)

        final_pipeline = build_model_registry(seed=self.config.seed, class_weight=self.config.positive_class_weight)[best_model_name]
        final_pipeline.fit(X_train_validation, y_train_validation)
        test_probabilities = final_pipeline.predict_proba(X_test)[:, 1]
        test_predictions = (test_probabilities >= 0.5).astype(int)
        test_metrics = compute_classification_metrics(y_test, test_predictions, test_probabilities)

        estimator = final_pipeline.named_steps["model"]
        importance_df = feature_importance_frame(estimator, feature_columns)
        report_path = save_feature_report(
            report_dir=self.config.report_dir,
            model_name=best_model_name,
            symbol=symbol,
            interval=interval,
            feature_importance=importance_df,
            validation_metrics=best_result["validation_metrics"],
            test_metrics=test_metrics,
        )

        artifact_stamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        parts = [best_model_name]
        if symbol:
            parts.append(symbol.replace("/", "_"))
        if interval:
            parts.append(interval)
        parts.append(artifact_stamp)
        artifact_path = artifact_dir / ("_".join(parts) + ".joblib")

        metadata = ModelArtifactMetadata(
            model_name=best_model_name,
            created_at=datetime.now(UTC).isoformat(),
            symbol=symbol,
            interval=interval,
            feature_columns=feature_columns,
            dataset_path=str(dataset_path),
            target=asdict(self.config.target),
            split=asdict(self.config.split),
            validation_metrics=best_result["validation_metrics"].to_dict(),
            test_metrics=test_metrics.to_dict(),
            train_rows=len(train_df),
            validation_rows=len(validation_df),
            test_rows=len(test_df),
            artifact_path=str(artifact_path),
            report_path=str(report_path),
        )

        joblib.dump({"pipeline": final_pipeline, "feature_columns": feature_columns, "metadata": metadata.to_dict()}, artifact_path)
        self.model_repo.save_run(metadata.to_dict())

        return {
            "artifact_path": artifact_path,
            "report_path": report_path,
            "metadata": metadata.to_dict(),
            "candidate_results": [
                {
                    "model_name": result["model_name"],
                    "validation_metrics": result["validation_metrics"].to_dict(),
                    "selection_score": result["selection_score"],
                }
                for result in candidate_results
            ],
            "split_summary": split_summary(train_df, validation_df, test_df),
        }


def save_labeled_dataset(
    labeled_df: pd.DataFrame,
    symbol: str | None = None,
    interval: str | None = None,
) -> Path:
    output_dir = Path("data/processed/models")
    output_dir.mkdir(parents=True, exist_ok=True)
    parts = ["targets"]
    if symbol:
        parts.append(symbol.replace("/", "_"))
    if interval:
        parts.append(interval)
    path = output_dir / ("_".join(parts) + ".csv")
    labeled_df.to_csv(path, index=False)
    return path
