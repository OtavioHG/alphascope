"""Compatibility models preserved for advanced research modules."""

from __future__ import annotations

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from alphascope.storage.database import Base as StorageBase


class FeatureRecord(StorageBase):
    __tablename__ = "feature_store"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    feature_name: Mapped[str] = mapped_column(String(128), index=True)
    feature_value: Mapped[float] = mapped_column(Float)
    timestamp: Mapped[object] = mapped_column(DateTime(timezone=True), index=True)
    online_ready: Mapped[bool] = mapped_column(Boolean, default=True)


class RegimeDetectionRecord(StorageBase):
    __tablename__ = "regimes_detected"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    timestamp: Mapped[object] = mapped_column(DateTime(timezone=True), index=True)
    regime_label: Mapped[str] = mapped_column(String(64))
    regime_confidence: Mapped[float] = mapped_column(Float)


class AnomalyDetectionRecord(StorageBase):
    __tablename__ = "anomalies_detected"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    timestamp: Mapped[object] = mapped_column(DateTime(timezone=True), index=True)
    anomaly_score: Mapped[float] = mapped_column(Float)
    anomaly_type: Mapped[str] = mapped_column(String(64), default="generic")


class MinedSignalRecord(StorageBase):
    __tablename__ = "mined_signals"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    signal_definition: Mapped[str] = mapped_column(String(255), index=True)
    support_count: Mapped[int] = mapped_column(Integer, default=0)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    source: Mapped[str] = mapped_column(String(64), default="research")


class StrategyCandidateRecord(StorageBase):
    __tablename__ = "strategy_candidates"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    strategy_id: Mapped[str] = mapped_column(String(128), index=True)
    strategy_name: Mapped[str] = mapped_column(String(255))
    expected_return: Mapped[float] = mapped_column(Float, default=0.0)
    risk_score: Mapped[float] = mapped_column(Float, default=0.0)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)


class DiscoveryRankingRecord(StorageBase):
    __tablename__ = "discovery_rankings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    strategy_id: Mapped[str] = mapped_column(String(128), index=True)
    rank_position: Mapped[int] = mapped_column(Integer, default=0)
    composite_score: Mapped[float] = mapped_column(Float, default=0.0)


class ExperimentRunRecord(StorageBase):
    __tablename__ = "experiment_runs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    experiment_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    strategy_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    score: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AlphaReportRecord(StorageBase):
    __tablename__ = "alpha_reports"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_name: Mapped[str] = mapped_column(String(255), unique=True)
    report_path: Mapped[str] = mapped_column(String(1024))
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())
