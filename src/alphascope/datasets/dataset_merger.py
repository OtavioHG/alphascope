"""Utilities for consolidating heterogeneous datasets."""

from __future__ import annotations

import re

import pandas as pd


class DatasetMerger:
    """Clean and merge multiple datasets into a single normalized frame."""

    def merge_news_frames(self, frames: list[pd.DataFrame]) -> pd.DataFrame:
        if not frames:
            return pd.DataFrame()
        non_empty = [frame.copy() for frame in frames if not frame.empty]
        if not non_empty:
            return pd.DataFrame()

        normalized = [self._normalize_news_columns(frame) for frame in non_empty]
        combined = pd.concat(normalized, ignore_index=True, sort=False)
        for column in ["title", "description", "text", "source", "link", "dataset_source"]:
            if column not in combined.columns:
                combined[column] = None
        if "timestamp" not in combined.columns:
            combined["timestamp"] = pd.NaT
        combined["timestamp"] = pd.to_datetime(combined["timestamp"], errors="coerce", utc=True)
        combined["content_key"] = (
            combined["title"].fillna("").astype(str).str.strip().str.lower()
            + "|"
            + combined["text"].fillna("").astype(str).str.strip().str.lower().str[:200]
        )
        combined = combined.drop_duplicates(subset=["content_key", "timestamp"], keep="first")
        combined["clean_text"] = combined.apply(self._compose_clean_text, axis=1)
        combined = combined.drop(columns=["content_key"])
        return combined.sort_values("timestamp", na_position="last").reset_index(drop=True)

    def _normalize_news_columns(self, frame: pd.DataFrame) -> pd.DataFrame:
        normalized = frame.copy()
        available_map = {
            source: target
            for source, target in {
                "headline": "title",
                "summary": "description",
                "content": "text",
                "published_at": "timestamp",
                "published": "timestamp",
                "url": "link",
                "domain": "source",
            }.items()
            if source in normalized.columns
        }
        return normalized.rename(columns=available_map)

    @staticmethod
    def _compose_clean_text(row: pd.Series) -> str:
        parts = [str(row.get("title", "") or ""), str(row.get("description", "") or ""), str(row.get("text", "") or "")]
        text = " ".join(part.strip() for part in parts if part and part.strip())
        return re.sub(r"\s+", " ", text).strip()
