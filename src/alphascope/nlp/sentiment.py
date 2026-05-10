"""Sentiment inference helpers for financial news."""

from __future__ import annotations

import logging

from transformers import pipeline

from alphascope.config.settings import settings

logger = logging.getLogger(__name__)


class NewsSentimentClassifier:
    """Classify sentiment with a pretrained transformers pipeline."""

    def __init__(self, model_name: str | None = None) -> None:
        self.model_name = model_name or settings.nlp_model_name
        try:
            self.classifier = pipeline("sentiment-analysis", model=self.model_name)
        except Exception as exc:
            logger.warning("Sentiment model %s unavailable; falling back to neutral mode: %s", self.model_name, exc)
            self.classifier = None

    def classify(self, text: str) -> dict[str, float | str]:
        if not text or self.classifier is None:
            return {"sentiment_label": "neutral", "sentiment_score": 0.5}
        try:
            result = self.classifier(text[:512])[0]
            label = str(result["label"]).lower()
            score = float(result["score"])
            return {"sentiment_label": label, "sentiment_score": score}
        except Exception as exc:
            logger.warning("Sentiment classification failed: %s", exc)
            return {"sentiment_label": "neutral", "sentiment_score": 0.5}
