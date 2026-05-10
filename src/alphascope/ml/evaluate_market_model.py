"""Evaluation utilities for market ML models."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score

from alphascope.datasets.market_dataset_builder import MARKET_FEATURE_COLUMNS
from alphascope.ml.dataset_builder import MarketDatasetBuilder
from alphascope.ml.model_registry import ModelRegistry


def evaluate_market_classifier(y_true: pd.Series, y_pred: np.ndarray, y_proba: np.ndarray) -> dict[str, float]:
    """Compute standard classification metrics for market models."""
    metrics = {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
    }
    if len(set(y_true.tolist())) > 1:
        metrics["roc_auc"] = float(roc_auc_score(y_true, y_proba))
    else:
        metrics["roc_auc"] = 0.5
    return metrics


class MarketModelEvaluator:
    """Evaluate a saved market model on a temporal test split."""

    def __init__(self, dataset_builder: MarketDatasetBuilder | None = None, registry: ModelRegistry | None = None) -> None:
        self.dataset_builder = dataset_builder or MarketDatasetBuilder()
        self.registry = registry or ModelRegistry()

    def evaluate(self, dataset: pd.DataFrame, artifact_path: str) -> dict[str, object]:
        train_frame, test_frame = self.dataset_builder.train_test_split(dataset)
        if test_frame.empty:
            raise RuntimeError("Evaluation dataset has no test partition.")
        model = self.registry.load_model(artifact_path)
        x_test = test_frame.loc[:, MARKET_FEATURE_COLUMNS]
        y_test = test_frame["up_move_target"].astype(int)
        y_pred = model.predict(x_test)
        y_proba = model.predict_proba(x_test)[:, 1]
        metrics = evaluate_market_classifier(y_true=y_test, y_pred=y_pred, y_proba=y_proba)
        predictions = test_frame.loc[:, ["timestamp", "symbol"]].copy()
        predictions["target"] = y_test
        predictions["prediction"] = y_pred
        predictions["probability"] = y_proba
        return {"metrics": metrics, "predictions": predictions}
