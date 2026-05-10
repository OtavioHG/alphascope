"""Helpers for loading Hugging Face datasets."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from alphascope.config.settings import settings


class HuggingFaceDatasetLoader:
    """Load Hugging Face datasets either from the datasets library or local exports."""

    def load_financial_phrasebank(self, split: str = "train") -> pd.DataFrame:
        """Load the financial phrasebank dataset when the datasets package is available."""
        try:
            from datasets import load_dataset
        except ImportError as exc:
            raise RuntimeError("The 'datasets' package is required to load Hugging Face datasets directly.") from exc

        dataset = load_dataset(settings.huggingface_sentiment_dataset, "sentences_allagree", split=split)
        frame = dataset.to_pandas()
        available_map = {source: target for source, target in {"sentence": "text", "label": "label"}.items() if source in frame.columns}
        frame = frame.rename(columns=available_map)
        frame["dataset_source"] = "huggingface_financial_phrasebank"
        return frame

    def load_export(self, path: str | Path) -> pd.DataFrame:
        """Load a locally exported Hugging Face dataset."""
        dataset_path = Path(path)
        suffix = dataset_path.suffix.lower()
        if suffix == ".jsonl":
            return pd.read_json(dataset_path, lines=True)
        if suffix == ".parquet":
            return pd.read_parquet(dataset_path)
        return pd.read_csv(dataset_path)

    def discover(self, directory: str | Path | None = None) -> list[Path]:
        """Discover locally available Hugging Face dataset exports."""
        base_dir = Path(directory) if directory else settings.hf_datasets_dir
        if not base_dir.exists():
            return []
        return sorted(
            [path for path in base_dir.rglob("*") if path.is_file() and path.suffix.lower() in {".csv", ".jsonl", ".parquet"}]
        )
