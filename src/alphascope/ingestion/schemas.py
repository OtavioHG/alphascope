"""Data contracts for market ingestion."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class IngestionRequest:
    symbol: str
    interval: str
    limit: int


@dataclass(frozen=True)
class IngestionResult:
    symbol: str
    interval: str
    rows: int
    frame: pd.DataFrame
