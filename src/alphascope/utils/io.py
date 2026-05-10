"""Simple IO helpers for AlphaScope V1."""

from __future__ import annotations

from pathlib import Path


def ensure_directory(path: str | Path) -> Path:
    """Create a directory if missing and return its path."""
    directory = Path(path)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def parse_csv_argument(value: str) -> list[str]:
    """Split a comma-separated CLI argument into uppercase tokens."""
    return [item.strip().upper() for item in value.split(",") if item.strip()]


def list_dataset_files(directory: str | Path, suffixes: tuple[str, ...] = (".csv", ".jsonl", ".parquet")) -> list[Path]:
    """List available dataset files recursively under a directory."""
    base_dir = Path(directory)
    if not base_dir.exists():
        return []
    return sorted([path for path in base_dir.rglob("*") if path.is_file() and path.suffix.lower() in suffixes])
