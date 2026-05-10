from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class TargetConfig:
    future_horizon: int = 4
    return_threshold: float = 0.015
    price_column: str = "close"
    group_column: str = "symbol"
    target_column: str = "target"


@dataclass(slots=True)
class TemporalSplitConfig:
    train_ratio: float = 0.70
    validation_ratio: float = 0.15
    test_ratio: float = 0.15
    timestamp_column: str = "timestamp"

    def validate(self) -> None:
        total = self.train_ratio + self.validation_ratio + self.test_ratio
        if abs(total - 1.0) > 1e-9:
            raise ValueError("Temporal split ratios must sum to 1.0")


@dataclass(slots=True)
class TrainingConfig:
    seed: int = 42
    model_names: tuple[str, ...] = (
        "logistic_regression",
        "random_forest",
        "gradient_boosting",
    )
    positive_class_weight: str | None = "balanced"
    artifact_dir: Path = Path("data/processed/models")
    report_dir: Path = Path("data/processed/model_reports")
    target: TargetConfig = field(default_factory=TargetConfig)
    split: TemporalSplitConfig = field(default_factory=TemporalSplitConfig)


@dataclass(slots=True)
class EvaluationMetrics:
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    roc_auc: float | None
    confusion_matrix: list[list[int]]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ModelArtifactMetadata:
    model_name: str
    created_at: str
    symbol: str | None
    interval: str | None
    feature_columns: list[str]
    dataset_path: str
    target: dict[str, Any]
    split: dict[str, Any]
    validation_metrics: dict[str, Any]
    test_metrics: dict[str, Any]
    train_rows: int
    validation_rows: int
    test_rows: int
    artifact_path: str
    report_path: str
    labeled_dataset_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class TradeRecord:
    timestamp: datetime
    symbol: str
    side: str
    price: float
    quantity: float
    fee_paid: float
    slippage_paid: float
    cash_after: float
    position_after: float
    realized_pnl: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["timestamp"] = self.timestamp.isoformat()
        return payload


@dataclass(slots=True)
class BacktestSummary:
    symbol: str
    model_name: str
    total_return: float
    cumulative_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    number_of_trades: int
    initial_cash: float
    final_equity: float
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
