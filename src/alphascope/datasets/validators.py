"""Validation helpers for external and processed datasets."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class DatasetValidationResult:
    """Structured validation output for a dataset."""

    valid: bool
    row_count: int
    duplicate_count: int
    missing_required: dict[str, int]
    warnings: list[str]


def validate_market_dataframe(frame: pd.DataFrame) -> DatasetValidationResult:
    """Validate the minimum schema for market datasets."""
    required = ["timestamp", "symbol", "open", "high", "low", "close", "volume"]
    warnings: list[str] = []
    if frame.empty:
        return DatasetValidationResult(False, 0, 0, {column: 0 for column in required}, ["dataset vazio"])

    checked = frame.copy()
    checked["timestamp"] = pd.to_datetime(checked.get("timestamp"), errors="coerce", utc=True)
    missing = {column: int(checked[column].isna().sum()) if column in checked.columns else len(checked) for column in required}
    duplicates = int(checked.duplicated(subset=[column for column in ["timestamp", "symbol", "interval"] if column in checked.columns]).sum())
    for column in ["open", "high", "low", "close", "volume"]:
        if column in checked.columns:
            checked[column] = pd.to_numeric(checked[column], errors="coerce")
            if checked[column].isna().any():
                warnings.append(f"coluna numerica com valores invalidos: {column}")
    if checked["timestamp"].isna().any():
        warnings.append("timestamps invalidos ou sem timezone")
    valid = all(value == 0 for value in missing.values())
    return DatasetValidationResult(valid, len(checked), duplicates, missing, warnings)


def validate_news_dataframe(frame: pd.DataFrame) -> DatasetValidationResult:
    """Validate the minimum schema for news datasets."""
    required_any = [("text", "description"), ("title",), ("timestamp",), ("source",)]
    warnings: list[str] = []
    if frame.empty:
        return DatasetValidationResult(False, 0, 0, {"title": 0, "text_or_description": 0, "timestamp": 0, "source": 0}, ["dataset vazio"])

    checked = frame.copy()
    checked["timestamp"] = pd.to_datetime(checked.get("timestamp"), errors="coerce", utc=True)
    missing = {
        "title": int(checked["title"].isna().sum()) if "title" in checked.columns else len(checked),
        "text_or_description": int(((checked.get("text").fillna("") == "") & (checked.get("description").fillna("") == "")).sum()) if {"text", "description"}.intersection(checked.columns) else len(checked),
        "timestamp": int(checked["timestamp"].isna().sum()),
        "source": int(checked["source"].isna().sum()) if "source" in checked.columns else len(checked),
    }
    duplicates = int(
        checked.duplicated(subset=[column for column in ["title", "timestamp", "source"] if column in checked.columns]).sum()
    )
    if checked["timestamp"].isna().any():
        warnings.append("timestamps invalidos ou sem timezone")
    if duplicates:
        warnings.append("duplicatas detectadas")
    valid = all(value == 0 for value in missing.values())
    return DatasetValidationResult(valid, len(checked), duplicates, missing, warnings)
