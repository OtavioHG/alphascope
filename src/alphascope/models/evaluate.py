from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score

from alphascope.domain.model_schemas import EvaluationMetrics


def compute_classification_metrics(
    y_true: pd.Series | np.ndarray,
    y_pred: pd.Series | np.ndarray,
    y_prob: pd.Series | np.ndarray,
) -> EvaluationMetrics:
    true_values = np.asarray(y_true)
    pred_values = np.asarray(y_pred)
    prob_values = np.asarray(y_prob)

    roc_auc: float | None
    if len(np.unique(true_values)) < 2:
        roc_auc = None
    else:
        roc_auc = float(roc_auc_score(true_values, prob_values))

    return EvaluationMetrics(
        accuracy=float(accuracy_score(true_values, pred_values)),
        precision=float(precision_score(true_values, pred_values, zero_division=0)),
        recall=float(recall_score(true_values, pred_values, zero_division=0)),
        f1_score=float(f1_score(true_values, pred_values, zero_division=0)),
        roc_auc=roc_auc,
        confusion_matrix=confusion_matrix(true_values, pred_values).tolist(),
    )


def model_selection_score(metrics: EvaluationMetrics) -> float:
    roc_component = metrics.roc_auc if metrics.roc_auc is not None else 0.0
    return (metrics.f1_score * 0.5) + (roc_component * 0.3) + (metrics.precision * 0.2)


def feature_importance_frame(fitted_model: Any, feature_columns: list[str]) -> pd.DataFrame:
    if hasattr(fitted_model, "feature_importances_"):
        values = fitted_model.feature_importances_
    elif hasattr(fitted_model, "coef_"):
        values = np.abs(np.ravel(fitted_model.coef_))
    else:
        values = np.zeros(len(feature_columns))

    return (
        pd.DataFrame({"feature": feature_columns, "importance": values})
        .sort_values("importance", ascending=False)
        .reset_index(drop=True)
    )


def save_feature_report(
    report_dir: str | Path,
    model_name: str,
    symbol: str | None,
    interval: str | None,
    feature_importance: pd.DataFrame,
    validation_metrics: EvaluationMetrics,
    test_metrics: EvaluationMetrics,
) -> Path:
    output_dir = Path(report_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    suffix_parts = [model_name]
    if symbol:
        suffix_parts.append(symbol.replace("/", "_"))
    if interval:
        suffix_parts.append(interval)
    path = output_dir / ("_".join(suffix_parts) + "_report.json")
    payload = {
        "model_name": model_name,
        "symbol": symbol,
        "interval": interval,
        "validation_metrics": validation_metrics.to_dict(),
        "test_metrics": test_metrics.to_dict(),
        "top_features": feature_importance.head(20).to_dict(orient="records"),
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path
