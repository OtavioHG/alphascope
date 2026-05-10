"""Inference pipeline for news sentiment and topic scoring."""

from __future__ import annotations

import pandas as pd

from alphascope.config.settings import settings
from alphascope.ml.news_model_inference import NewsModelInference
from alphascope.nlp.sentiment import NewsSentimentClassifier
from alphascope.nlp.topics import NewsTopicClassifier


class NewsInferenceEngine:
    """Score news items for sentiment, topic and potential impact."""

    def __init__(self) -> None:
        self.sentiment = NewsSentimentClassifier()
        self.topics = NewsTopicClassifier()
        self.supervised = NewsModelInference() if settings.news_model_path.exists() else None

    def score_frame(self, news_frame: pd.DataFrame) -> pd.DataFrame:
        if news_frame.empty:
            return news_frame

        scored = news_frame.copy()
        sentiment_labels = []
        sentiment_scores = []
        topic_labels = []
        related_assets = []
        impact_scores = []

        for row in scored.itertuples(index=False):
            text = " ".join(
                str(value)
                for value in [getattr(row, "title", ""), getattr(row, "description", ""), getattr(row, "text", "")]
                if value
            )
            sentiment = self.sentiment.classify(text)
            topic = self.topics.classify_topic(text)
            asset = self.topics.extract_asset(text)
            impact = abs(float(sentiment["sentiment_score"]) - 0.5) * (1.2 if asset else 1.0)

            sentiment_labels.append(sentiment["sentiment_label"])
            sentiment_scores.append(sentiment["sentiment_score"])
            topic_labels.append(topic)
            related_assets.append(asset)
            impact_scores.append(impact)

        scored["sentiment_label"] = sentiment_labels
        scored["sentiment_score"] = sentiment_scores
        scored["topic_label"] = topic_labels
        scored["related_asset"] = related_assets
        scored["impact_score"] = impact_scores
        if self.supervised is not None:
            scored = self.supervised.score_frame(scored)
        return scored
