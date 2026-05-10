import pytest
import pandas as pd
import requests
from unittest.mock import MagicMock, patch
from alphascope.news_sources.gdelt_client import GDELTNewsClient
from alphascope.automation.continuous_pipeline import ContinuousPipeline, ContinuousPipelineConfig

@pytest.fixture
def gdelt_client():
    return GDELTNewsClient()

def test_gdelt_empty_response(gdelt_client):
    with patch.object(gdelt_client.session, 'get') as mock_get:
        mock_get.return_value.text = ""
        mock_get.return_value.status_code = 200
        df = gdelt_client.fetch_articles("bitcoin")
        assert isinstance(df, pd.DataFrame)
        assert df.empty

def test_gdelt_missing_articles_field(gdelt_client):
    with patch.object(gdelt_client.session, 'get') as mock_get:
        mock_get.return_value.json.return_value = {"status": "ok"}
        mock_get.return_value.text = '{"status": "ok"}'
        mock_get.return_value.status_code = 200
        df = gdelt_client.fetch_articles("bitcoin")
        assert df.empty

def test_gdelt_articles_not_a_list(gdelt_client):
    with patch.object(gdelt_client.session, 'get') as mock_get:
        mock_get.return_value.json.return_value = {"articles": "not a list"}
        mock_get.return_value.text = '{"articles": "not a list"}'
        mock_get.return_value.status_code = 200
        df = gdelt_client.fetch_articles("bitcoin")
        assert df.empty

def test_gdelt_json_decode_error(gdelt_client):
    with patch.object(gdelt_client.session, 'get') as mock_get:
        mock_get.return_value.json.side_effect = requests.exceptions.JSONDecodeError("msg", "doc", 0)
        mock_get.return_value.text = "invalid json {"
        mock_get.return_value.status_code = 200
        df = gdelt_client.fetch_articles("bitcoin")
        assert df.empty

def test_gdelt_timeout(gdelt_client):
    with patch.object(gdelt_client.session, 'get') as mock_get:
        mock_get.side_effect = requests.exceptions.ConnectTimeout()
        df = gdelt_client.fetch_articles("bitcoin")
        assert df.empty

def test_gdelt_429_rate_limit(gdelt_client):
    with patch.object(gdelt_client.session, 'get') as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_response)
        mock_get.return_value = mock_response
        
        df = gdelt_client.fetch_articles("bitcoin")
        assert df.empty

def test_gdelt_cache(gdelt_client):
    with patch.object(gdelt_client.session, 'get') as mock_get:
        mock_get.return_value.json.return_value = {"articles": [{"title": "Test"}]}
        mock_get.return_value.text = '{"articles": [{"title": "Test"}]}'
        mock_get.return_value.status_code = 200
        
        df1 = gdelt_client.fetch_articles("bitcoin")
        assert len(df1) == 1
        
        # Second call should use cache and NOT hit the network
        mock_get.reset_mock()
        mock_get.return_value.status_code = 500
        
        df2 = gdelt_client.fetch_articles("bitcoin")
        assert len(df2) == 1
        assert df2.iloc[0]["title"] == "Test"
        mock_get.assert_not_called()

@patch("alphascope.datasets.news_dataset_builder.NewsDatasetBuilder.fetch_gdelt")
def test_pipeline_resilience_to_news_failure(mock_fetch):
    mock_fetch.side_effect = Exception("GDELT Down")
    
    config = ContinuousPipelineConfig(
        cycle_interval_seconds=1,
        news_refresh_interval_seconds=1,
        symbols=["BTCUSDT"],
        timeframe="1h",
        candle_limit=10,
        enable_news=True,
    )
    
    mock_repo = MagicMock()
    mock_pipeline = MagicMock()
    mock_builder = MagicMock()
    mock_inference = MagicMock()
    
    mock_builder.fetch_gdelt.side_effect = Exception("GDELT Down")
    
    # Mocking write_state to avoid file I/O
    with patch("alphascope.automation.continuous_pipeline.ContinuousPipeline._write_state"):
        cp = ContinuousPipeline(
            config=config,
            repository=mock_repo,
            pipeline=mock_pipeline,
            news_builder=mock_builder,
            news_inference=mock_inference,
            state_path="data/runtime/test_state.json"
        )
        
        result = cp.run_cycle()
        
        assert result.success is True
        assert result.news_rows == 0
        mock_builder.fetch_gdelt.assert_called()
