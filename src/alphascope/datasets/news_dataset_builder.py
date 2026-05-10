"""Build consolidated news datasets from multiple free sources."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from alphascope.config.settings import settings
from alphascope.core.logger import get_logger
from alphascope.datasets.dataset_merger import DatasetMerger
from alphascope.datasets.parquet_utils import export_dataset
from alphascope.datasets.validators import validate_news_dataframe
from alphascope.news_sources.gdelt_client import GDELTNewsClient
from alphascope.news_sources.huggingface_loader import HuggingFaceDatasetLoader
from alphascope.news_sources.kaggle_loader import KaggleDatasetLoader

logger = get_logger(__name__)


class NewsDatasetBuilder:
    """Fetch, load and consolidate news data into a training-ready dataset."""

    def __init__(
        self,
        gdelt_client: GDELTNewsClient | None = None,
        huggingface_loader: HuggingFaceDatasetLoader | None = None,
        kaggle_loader: KaggleDatasetLoader | None = None,
        merger: DatasetMerger | None = None,
    ) -> None:
        self.gdelt_client = gdelt_client or GDELTNewsClient()
        self.huggingface_loader = huggingface_loader or HuggingFaceDatasetLoader()
        self.kaggle_loader = kaggle_loader or KaggleDatasetLoader()
        self.merger = merger or DatasetMerger()
        self.base_dir = settings.news_data_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def fetch_gdelt(self, query: str, max_records: int = 50, days: int = 1) -> pd.DataFrame:
        """Fetch recent GDELT news."""
        return self.gdelt_client.fetch_articles(query=query, max_records=max_records, days=days)

    def build(
        self,
        *,
        gdelt_query: str | None = None,
        gdelt_days: int = 1,
        gdelt_limit: int = 50,
        include_huggingface_financial_phrasebank: bool = False,
        huggingface_export_path: str | Path | None = None,
        kaggle_export_path: str | Path | None = None,
        export: bool = True,
        filename: str = "news_training_dataset.csv",
    ) -> pd.DataFrame:
        """Build a consolidated news dataset from configured sources."""
        frames: list[pd.DataFrame] = []
        if gdelt_query:
            try:
                frames.append(self.fetch_gdelt(query=gdelt_query, max_records=gdelt_limit, days=gdelt_days))
            except Exception as exc:
                logger.warning("GDELT fetch failed: %s", exc)
        if include_huggingface_financial_phrasebank:
            try:
                frames.append(self.huggingface_loader.load_financial_phrasebank())
            except Exception as exc:
                logger.warning("Hugging Face dataset load failed: %s", exc)
        if huggingface_export_path:
            frames.append(self.huggingface_loader.load_export(huggingface_export_path))
        if kaggle_export_path:
            frames.append(self.kaggle_loader.load(kaggle_export_path))

        dataset = self.merger.merge_news_frames(frames)
        if export and not dataset.empty:
            self.save_dataset(dataset, filename)
        return dataset

    def import_external_news_data(
        self,
        input_path: str | Path,
        *,
        output_path: str | Path | None = None,
    ) -> Path:
        """Normalize and persist an external news dataset."""
        dataset = self.load_local_dataset(input_path)
        dataset = self.merger.merge_news_frames([dataset])
        validation = validate_news_dataframe(dataset)
        if not validation.valid:
            raise RuntimeError(f"Invalid imported news dataset: {validation}")
        target_path = Path(output_path) if output_path else settings.news_dataset_path
        export_dataset(dataset, target_path, include_csv=True)
        return target_path

    def load_local_dataset(self, path: str | Path) -> pd.DataFrame:
        """Load a local CSV, JSONL or parquet dataset."""
        dataset_path = Path(path)
        suffix = dataset_path.suffix.lower()
        if suffix == ".jsonl":
            return pd.read_json(dataset_path, lines=True)
        if suffix == ".parquet":
            return pd.read_parquet(dataset_path)
        return pd.read_csv(dataset_path)

    def save_dataset(self, frame: pd.DataFrame, filename: str) -> Path:
        """Persist a dataset into the configured news data directory."""
        path = self.base_dir / filename
        export_dataset(frame, path, include_csv=path.suffix.lower() != ".csv")
        logger.info("Saved news dataset to %s", path)
        return path
