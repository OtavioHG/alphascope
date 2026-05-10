from __future__ import annotations

import pandas as pd

from alphascope.config.settings import settings
from alphascope.ml.news_model_inference import NewsModelInference
from alphascope.ml.news_model_training import NewsModelTrainer


def test_news_model_training_and_inference_roundtrip() -> None:
    dataset = pd.DataFrame(
        [
            {"clean_text": "bitcoin surges on strong demand", "label": 2},
            {"clean_text": "market outlook improves with inflows", "label": 2},
            {"clean_text": "exchange hacked and panic spreads", "label": 0},
            {"clean_text": "token collapses after exploit", "label": 0},
            {"clean_text": "traders remain cautious after choppy session", "label": 1},
        ]
    )

    result = NewsModelTrainer().train(dataset, text_column="clean_text", label_column="label")

    assert result["artifact_path"] == str(settings.news_model_path)

    frame = pd.DataFrame([{"clean_text": "bitcoin gains as demand improves"}])
    scored = NewsModelInference().score_frame(frame, text_column="clean_text")

    assert "supervised_sentiment_label" in scored.columns
    assert "supervised_sentiment_score" in scored.columns
    assert len(scored) == 1
