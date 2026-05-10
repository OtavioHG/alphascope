"""Schemas for market ML workflows."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True)
class MarketTargetConfig:
    horizon_bars: int
    threshold_pct: float
    target_name: str = "up_move_target"


@dataclass(frozen=True)
class TrainSplitConfig:
    train_fraction: float = 0.8


@dataclass(frozen=True)
class MarketModelMetadata:
    model_name: str
    target_name: str
    feature_columns: list[str]
    symbols: list[str]
    train_rows: int
    test_rows: int
    metrics: dict[str, float]
    artifact_path: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    extra_metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["created_at"] = self.created_at.isoformat()
        return payload
