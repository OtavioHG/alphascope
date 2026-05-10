import pytest
from unittest.mock import MagicMock, patch
from alphascope.nlp.sentiment import NewsSentimentClassifier
from alphascope.nlp.topic import NewsTopicClassifier

@patch("alphascope.nlp.sentiment.pipeline")
def test_sentiment_classification(mock_pipeline):
    # Setup mock
    mock_clf = MagicMock()
    mock_clf.return_value = [{"label": "POSITIVE", "score": 0.99}]
    mock_pipeline.return_value = mock_clf
    
    classifier = NewsSentimentClassifier()
    result = classifier.classify("Bitcoin is going to the moon!")
    
    assert result["sentiment_label"] == "positive"
    assert result["sentiment_score"] == 0.99

@patch("alphascope.nlp.topic.pipeline")
def test_topic_classification(mock_pipeline):
    # Setup mock
    mock_clf = MagicMock()
    mock_clf.return_value = {"labels": ["technology"], "scores": [0.9]}
    mock_pipeline.return_value = mock_clf
    
    classifier = NewsTopicClassifier()
    result = classifier.classify_topic("New blockchain update released.")
    
    assert result == "technology"

def test_asset_extraction():
    classifier = NewsTopicClassifier()
    assert classifier.extract_asset("Bitcoin price crashes") == "BTC"
    assert classifier.extract_asset("ETH hits all time high") == "ETH"
    assert classifier.extract_asset("No crypto mentioned") is None
