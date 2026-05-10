"""News data source clients for AlphaScope."""

from alphascope.news_sources.gdelt_client import GDELTNewsClient
from alphascope.news_sources.huggingface_loader import HuggingFaceDatasetLoader
from alphascope.news_sources.kaggle_loader import KaggleDatasetLoader

__all__ = ["GDELTNewsClient", "HuggingFaceDatasetLoader", "KaggleDatasetLoader"]
