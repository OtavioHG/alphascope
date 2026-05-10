from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import pandas as pd

from alphascope.models.dataset import Phase3DatasetBuilder


def load_model_artifact(artifact_path: str | Path) -> dict[str, Any]:
    path = Path(artifact_path)
    if not path.exists():
        raise FileNotFoundError(f"Model artifact not found: {path}")
    return joblib.load(path)


def predict_from_dataframe(
    artifact: dict[str, Any],
    df: pd.DataFrame,
    latest_only: bool = True,
) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(
            columns=[
                "timestamp",
                "symbol",
                "predicted_label",
                "predicted_probability",
                "confidence_score",
                "model_name",
                "model_version",
            ]
        )

    feature_columns = artifact["feature_columns"]
    dataset = df.sort_values(["symbol", "timestamp"]).copy()
    probabilities = artifact["pipeline"].predict_proba(dataset[feature_columns])[:, 1]
    dataset["predicted_label"] = (probabilities >= 0.5).astype(int)
    dataset["predicted_probability"] = probabilities
    dataset["confidence_score"] = abs(probabilities - 0.5) * 2.0
    dataset["model_name"] = artifact["metadata"]["model_name"]
    dataset["model_version"] = artifact["metadata"]["created_at"]

    if latest_only:
        dataset = dataset.groupby("symbol", as_index=False).tail(1).reset_index(drop=True)

    return dataset


def predict_from_dataset_path(
    artifact_path: str | Path,
    dataset_path: str | Path,
    symbol: str | None = None,
    interval: str | None = None,
    latest_only: bool = True,
) -> pd.DataFrame:
    artifact = load_model_artifact(artifact_path)
    builder = Phase3DatasetBuilder(feature_columns=artifact["feature_columns"])
    dataset = builder.load_dataset(str(dataset_path))
    dataset = builder.prepare_dataset(dataset, symbol=symbol, interval=interval)
    return predict_from_dataframe(artifact, dataset, latest_only=latest_only)
