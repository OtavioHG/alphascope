from alphascope.config.settings import settings
from alphascope.ingestion.news_ingestor import NewsIngestor
from alphascope.ingestion.coingecko_ingestor import CoinGeckoIngestor
import pytest

def test_settings_load():
    assert settings.APP_ENV in ["development", "production", "test"]

def test_news_ingestor_init():
    ingestor = NewsIngestor(api_key="test_key")
    assert ingestor.api_key == "test_key"

def test_coingecko_ingestor_init():
    ingestor = CoinGeckoIngestor(api_key="test_key")
    assert ingestor.api_key == "test_key"
    assert "x-cg-demo-api-key" in ingestor.headers
