"""Utilities for efficient processing of large tabular datasets."""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

import pandas as pd

from alphascope.core.logger import get_logger
from alphascope.datasets.validators import DatasetValidationResult, validate_market_dataframe, validate_news_dataframe

logger = get_logger(__name__)

DEFAULT_MARKET_SCHEMA_MAP = {
    "date": "timestamp",
    "time": "timestamp",
    "datetime": "timestamp",
    "open_time": "timestamp",
    "symbol_name": "symbol",
    "pair": "symbol",
    "ticker": "symbol",
    "base_volume": "volume",
}


def normalize_columns(frame: pd.DataFrame, schema_map: dict[str, str] | None = None) -> pd.DataFrame:
    """Normalize common market dataset aliases into the internal schema."""
    rename_map = DEFAULT_MARKET_SCHEMA_MAP.copy()
    if schema_map:
        rename_map.update(schema_map)
    available = {column: rename_map[column] for column in frame.columns if column in rename_map}
    return frame.rename(columns=available)


def optimize_dataframe_memory(frame: pd.DataFrame) -> pd.DataFrame:
    """Reduce dataframe memory usage by downcasting numerics when possible."""
    optimized = frame.copy()
    for column in optimized.select_dtypes(include=["int64", "int32"]).columns:
        optimized[column] = pd.to_numeric(optimized[column], downcast="integer")
    for column in optimized.select_dtypes(include=["float64", "float32"]).columns:
        optimized[column] = pd.to_numeric(optimized[column], downcast="float")
    return optimized


def read_csv_in_chunks(
    path: str | Path,
    *,
    columns: list[str] | None = None,
    chunk_size: int = 100_000,
    schema_map: dict[str, str] | None = None,
) -> Iterator[pd.DataFrame]:
    """Read a large CSV incrementally."""
    dataset_path = Path(path)
    for chunk in pd.read_csv(dataset_path, usecols=columns, chunksize=chunk_size):
        normalized = normalize_columns(chunk, schema_map=schema_map)
        yield optimize_dataframe_memory(normalized)


def read_dataset(
    path: str | Path,
    *,
    columns: list[str] | None = None,
    chunk_size: int = 100_000,
    schema_map: dict[str, str] | None = None,
) -> Iterator[pd.DataFrame]:
    """Read CSV or Parquet data, yielding one or more frames."""
    dataset_path = Path(path)
    suffix = dataset_path.suffix.lower()
    if suffix == ".csv":
        yield from read_csv_in_chunks(dataset_path, columns=columns, chunk_size=chunk_size, schema_map=schema_map)
        return
    if suffix == ".parquet":
        frame = pd.read_parquet(dataset_path, columns=columns)
        yield optimize_dataframe_memory(normalize_columns(frame, schema_map=schema_map))
        return
    raise ValueError(f"Unsupported dataset format: {dataset_path.suffix}")


def export_dataset(frame: pd.DataFrame, path: str | Path, *, include_csv: bool = False) -> None:
    """Export a dataframe primarily as Parquet and optionally as CSV."""
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.suffix.lower() == ".csv":
        frame.to_csv(output_path, index=False)
    else:
        try:
            frame.to_parquet(output_path, index=False)
        except (ImportError, ModuleNotFoundError) as exc:
            csv_fallback = output_path.with_suffix(".csv")
            frame.to_csv(csv_fallback, index=False)
            logger.warning("Parquet export unavailable for %s (%s). Saved CSV fallback to %s", output_path, exc, csv_fallback)
            return
    if include_csv and output_path.suffix.lower() != ".csv":
        frame.to_csv(output_path.with_suffix(".csv"), index=False)
    logger.info("Exported dataset to %s", output_path)


def convert_csv_to_parquet(
    csv_path: str | Path,
    parquet_path: str | Path,
    *,
    columns: list[str] | None = None,
    chunk_size: int = 100_000,
    schema_map: dict[str, str] | None = None,
) -> Path:
    """Convert a large CSV file to Parquet through incremental loading."""
    frames = list(read_csv_in_chunks(csv_path, columns=columns, chunk_size=chunk_size, schema_map=schema_map))
    if not frames:
        raise RuntimeError(f"No rows found in {csv_path}")
    combined = pd.concat(frames, ignore_index=True)
    export_dataset(combined, parquet_path)
    return Path(parquet_path)


def validate_dataset_file(path: str | Path, *, dataset_type: str) -> DatasetValidationResult:
    """Validate a market or news dataset from disk."""
    frames = list(read_dataset(path))
    if not frames:
        raise RuntimeError(f"No rows found in dataset: {path}")
    dataset = pd.concat(frames, ignore_index=True)
    if dataset_type == "market":
        return validate_market_dataframe(dataset)
    if dataset_type == "news":
        return validate_news_dataframe(dataset)
    raise ValueError(f"Unsupported dataset_type: {dataset_type}")
