"""Inference helpers for supervised news sentiment models."""

from __future__ import annotations

import joblib
import pandas as pd

from alphascope.config.settings import settings


class NewsModelInference:
    """Load a persisted news model and score text rows."""

    def __init__(self, artifact_path: str | None = None) -> None:
        self.artifact_path = artifact_path or str(settings.news_model_path)
        self.model = joblib.load(self.artifact_path)

    def score_frame(self, frame: pd.DataFrame, *, text_column: str | None = None) -> pd.DataFrame:
        if frame.empty:
            return frame
        resolved_text_column = self._resolve_text_column(frame, text_column)
        scored = frame.copy()
        predictions = self.model.predict(scored[resolved_text_column].fillna(""))
        scored["supervised_sentiment_label"] = predictions

        if hasattr(self.model, "predict_proba"):
            probabilities = self.model.predict_proba(scored[resolved_text_column].fillna(""))
            scored["supervised_sentiment_score"] = probabilities.max(axis=1)
        else:
            scored["supervised_sentiment_score"] = None
        return scored

    @staticmethod
    def _resolve_text_column(dataset: pd.DataFrame, requested: str | None) -> str:
        if requested and requested in dataset.columns:
            return requested
        for column in ["clean_text", "text", "title"]:
            if column in dataset.columns:
                return column
        raise RuntimeError("No suitable text column found. Expected one of: clean_text, text, title.")
