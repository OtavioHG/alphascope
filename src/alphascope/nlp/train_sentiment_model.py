"""Supervised training for a lightweight news sentiment model."""

from __future__ import annotations

import json

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from alphascope.config.settings import settings
from alphascope.core.logger import get_logger

logger = get_logger(__name__)


class NewsSentimentTrainer:
    """Train a simple supervised sentiment classifier from labeled news data."""

    def train(self, dataset: pd.DataFrame, text_column: str = "text", label_column: str = "label") -> dict[str, object]:
        if dataset.empty:
            raise RuntimeError("News sentiment dataset is empty.")
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
        model.fit(train[text_column].fillna(""), train[label_column])
        accuracy = float(model.score(test[text_column].fillna(""), test[label_column]))

        artifact_path = settings.nlp_model_dir / "news_sentiment_model.joblib"
        metadata_path = settings.nlp_model_dir / "news_sentiment_model.json"
        joblib.dump(model, artifact_path)
        metadata_path.write_text(
            json.dumps(
                {
                    "artifact_path": str(artifact_path),
                    "accuracy": accuracy,
                    "text_column": text_column,
                    "label_column": label_column,
                    "train_rows": len(train),
                    "test_rows": len(test),
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        logger.info("Saved supervised news sentiment model to %s", artifact_path)
        return {"artifact_path": str(artifact_path), "metadata_path": str(metadata_path), "accuracy": accuracy}
