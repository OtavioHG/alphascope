"""Supervised training pipeline for news sentiment models."""

from __future__ import annotations

import json

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score
from sklearn.pipeline import Pipeline

from alphascope.config.settings import settings
from alphascope.core.logger import get_logger
from alphascope.datasets.news_dataset_builder import NewsDatasetBuilder

logger = get_logger(__name__)


class NewsModelTrainer:
    """Train and persist a lightweight supervised news sentiment model."""

    def __init__(self, dataset_builder: NewsDatasetBuilder | None = None) -> None:
        self.dataset_builder = dataset_builder or NewsDatasetBuilder()

    def train(
        self,
        dataset: pd.DataFrame,
        *,
        text_column: str | None = None,
        label_column: str = "label",
    ) -> dict[str, object]:
        if dataset.empty:
            raise RuntimeError("News sentiment dataset is empty.")
        if label_column not in dataset.columns:
            raise RuntimeError(f"Required label column not found: {label_column}")

        resolved_text_column = self._resolve_text_column(dataset, text_column)
        ordered = dataset.copy().reset_index(drop=True)
        split_index = max(1, int(len(ordered) * settings.training_train_fraction))
        train = ordered.iloc[:split_index]
        test = ordered.iloc[split_index:]
        if test.empty:
            raise RuntimeError("News sentiment dataset has no test partition.")

        model = Pipeline(
            steps=[
                ("vectorizer", TfidfVectorizer(max_features=5000, ngram_range=(1, 2))),
                ("classifier", LogisticRegression(max_iter=1000)),
            ]
        )
        model.fit(train[resolved_text_column].fillna(""), train[label_column])
        predictions = model.predict(test[resolved_text_column].fillna(""))
        accuracy = float(accuracy_score(test[label_column], predictions))
        f1 = float(f1_score(test[label_column], predictions, average="weighted", zero_division=0))

        artifact_path = settings.news_model_path
        metadata_path = artifact_path.with_suffix(".json")
        joblib.dump(model, artifact_path)
        metadata_path.write_text(
            json.dumps(
                {
                    "artifact_path": str(artifact_path),
                    "text_column": resolved_text_column,
                    "label_column": label_column,
                    "train_rows": len(train),
                    "test_rows": len(test),
                    "accuracy": accuracy,
                    "f1_weighted": f1,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        logger.info("Saved news model to %s", artifact_path)
        return {
            "artifact_path": str(artifact_path),
            "metadata_path": str(metadata_path),
            "accuracy": accuracy,
            "f1_weighted": f1,
        }

    @staticmethod
    def _resolve_text_column(dataset: pd.DataFrame, requested: str | None) -> str:
        if requested and requested in dataset.columns:
            return requested
        for column in ["clean_text", "text", "title"]:
            if column in dataset.columns:
                return column
        raise RuntimeError("No suitable text column found. Expected one of: clean_text, text, title.")
