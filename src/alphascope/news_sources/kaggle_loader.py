"""Helpers for loading Kaggle-exported news datasets."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from alphascope.config.settings import settings


class KaggleDatasetLoader:
    """Load Kaggle datasets exported locally as CSV, JSONL or parquet."""

    def load(self, path: str | Path) -> pd.DataFrame:
        dataset_path = Path(path)
        suffix = dataset_path.suffix.lower()
        if suffix == ".jsonl":
            return pd.read_json(dataset_path, lines=True)
        if suffix == ".parquet":
            return pd.read_parquet(dataset_path)
        return pd.read_csv(dataset_path)

    def discover(self, directory: str | Path | None = None) -> list[Path]:
        """Discover locally available Kaggle dataset exports."""
        base_dir = Path(directory) if directory else settings.kaggle_data_dir
        if not base_dir.exists():
            return []
        return sorted(
            [path for path in base_dir.rglob("*") if path.is_file() and path.suffix.lower() in {".csv", ".jsonl", ".parquet"}]
        )
