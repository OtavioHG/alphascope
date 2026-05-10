from __future__ import annotations

from sqlalchemy import Boolean, DateTime, Float, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from alphascope.storage.database import StorageBase


class MarketCandleRecord(StorageBase):
    __tablename__ = "market_candles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    interval: Mapped[str] = mapped_column(String(16), index=True)
    timestamp: Mapped[str] = mapped_column(DateTime(timezone=True), index=True)
    open: Mapped[float] = mapped_column(Float)
    high: Mapped[float] = mapped_column(Float)
    low: Mapped[float] = mapped_column(Float)
    close: Mapped[float] = mapped_column(Float)
    volume: Mapped[float] = mapped_column(Float)

    __table_args__ = (Index("idx_market_candles_symbol_interval_timestamp", "symbol", "interval", "timestamp", unique=True),)


class NewsDataRecord(StorageBase):
    __tablename__ = "news_data"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(512))
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    url: Mapped[str] = mapped_column(String(1024), unique=True)
    source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    asset: Mapped[str | None] = mapped_column(String(32), nullable=True)
    published_at: Mapped[str] = mapped_column(DateTime(timezone=True), index=True)


class TechnicalFeatureRecord(StorageBase):
    __tablename__ = "technical_features_v2"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    timestamp: Mapped[str] = mapped_column(DateTime(timezone=True), index=True)
    pct_return: Mapped[float | None] = mapped_column(Float, nullable=True)
    ma_short: Mapped[float | None] = mapped_column(Float, nullable=True)
    ma_long: Mapped[float | None] = mapped_column(Float, nullable=True)
    rsi: Mapped[float | None] = mapped_column(Float, nullable=True)
    macd: Mapped[float | None] = mapped_column(Float, nullable=True)
    macd_signal: Mapped[float | None] = mapped_column(Float, nullable=True)
    bb_upper: Mapped[float | None] = mapped_column(Float, nullable=True)
    bb_lower: Mapped[float | None] = mapped_column(Float, nullable=True)
    volatility: Mapped[float | None] = mapped_column(Float, nullable=True)
    volume_avg: Mapped[float | None] = mapped_column(Float, nullable=True)
    relative_volume: Mapped[float | None] = mapped_column(Float, nullable=True)
    momentum: Mapped[float | None] = mapped_column(Float, nullable=True)


class SentimentScoreRecord(StorageBase):
    __tablename__ = "sentiment_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    news_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    symbol: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    sentiment_label: Mapped[str] = mapped_column(String(32))
    sentiment_score: Mapped[float] = mapped_column(Float)
    topic: Mapped[str | None] = mapped_column(String(128), nullable=True)
    timestamp: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ModelPredictionRecord(StorageBase):
    __tablename__ = "model_predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    interval: Mapped[str] = mapped_column(String(16), default="1h", index=True)
    timestamp: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    predicted_label: Mapped[int] = mapped_column(Integer)
    predicted_probability: Mapped[float] = mapped_column(Float)
    confidence_score: Mapped[float] = mapped_column(Float)
    model_name: Mapped[str] = mapped_column(String(128))
    model_version: Mapped[str] = mapped_column(String(128), default="v1")


class AssetRankingRecord(StorageBase):
    __tablename__ = "asset_rankings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    interval: Mapped[str] = mapped_column(String(16), default="1h", index=True)
    timestamp: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    predicted_probability: Mapped[float] = mapped_column(Float)
    opportunity_score: Mapped[float] = mapped_column(Float)
    risk_score: Mapped[float] = mapped_column(Float)
    final_score: Mapped[float] = mapped_column(Float)


class PortfolioSnapshotRecord(StorageBase):
    __tablename__ = "portfolio_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    timestamp: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    total_equity: Mapped[float] = mapped_column(Float)
    available_capital: Mapped[float] = mapped_column(Float)
    portfolio_return: Mapped[float] = mapped_column(Float)
    portfolio_value: Mapped[float] = mapped_column(Float)


class PortfolioPositionRecord(StorageBase):
    __tablename__ = "portfolio_positions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    quantity: Mapped[float] = mapped_column(Float)
    entry_price: Mapped[float] = mapped_column(Float)
    current_price: Mapped[float] = mapped_column(Float, default=0.0)
    unrealized_pnl: Mapped[float] = mapped_column(Float, default=0.0)
    allocation_amount: Mapped[float] = mapped_column(Float, default=0.0)
    opened_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    status: Mapped[str] = mapped_column(String(32), default="OPEN")


class TradeHistoryRecord(StorageBase):
    __tablename__ = "trade_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trade_id: Mapped[str] = mapped_column(String(128), unique=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    side: Mapped[str] = mapped_column(String(16))
    entry_price: Mapped[float] = mapped_column(Float)
    exit_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    quantity: Mapped[float] = mapped_column(Float)
    pnl: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(32))
    timestamp: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class OrderRecord(StorageBase):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[str] = mapped_column(String(128), unique=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    side: Mapped[str] = mapped_column(String(16))
    order_type: Mapped[str] = mapped_column(String(16))
    quantity: Mapped[float] = mapped_column(Float)
    price: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(32))
    exchange_name: Mapped[str] = mapped_column(String(32))
    timestamp: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())


class BacktestResultRecord(StorageBase):
    __tablename__ = "backtest_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    model_name: Mapped[str] = mapped_column(String(128))
    total_return: Mapped[float] = mapped_column(Float)
    sharpe_ratio: Mapped[float] = mapped_column(Float)
    max_drawdown: Mapped[float] = mapped_column(Float)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())


class OptimizationResultRecord(StorageBase):
    __tablename__ = "optimization_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    optimization_type: Mapped[str] = mapped_column(String(64))
    params: Mapped[str] = mapped_column(Text)
    score: Mapped[float] = mapped_column(Float)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())


class FeatureRecord(StorageBase):
    __tablename__ = "feature_store"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    feature_name: Mapped[str] = mapped_column(String(128), index=True)
    feature_value: Mapped[float] = mapped_column(Float)
    timestamp: Mapped[str] = mapped_column(DateTime(timezone=True), index=True)
    online_ready: Mapped[bool] = mapped_column(Boolean, default=True)


class RegimeDetectionRecord(StorageBase):
    __tablename__ = "regimes_detected"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    timestamp: Mapped[str] = mapped_column(DateTime(timezone=True), index=True)
    regime_label: Mapped[str] = mapped_column(String(64))
    regime_confidence: Mapped[float] = mapped_column(Float)


class AnomalyDetectionRecord(StorageBase):
    __tablename__ = "anomalies_detected"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    timestamp: Mapped[str] = mapped_column(DateTime(timezone=True), index=True)
    anomaly_score: Mapped[float] = mapped_column(Float)
    anomaly_type: Mapped[str] = mapped_column(String(64))
    anomaly_window: Mapped[int] = mapped_column(Integer)


class MinedSignalRecord(StorageBase):
    __tablename__ = "mined_signals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    signal_definition: Mapped[str] = mapped_column(String(128), index=True)
    sample_count: Mapped[int] = mapped_column(Integer)
    win_rate: Mapped[float] = mapped_column(Float)
    avg_return: Mapped[float] = mapped_column(Float)
    sharpe: Mapped[float] = mapped_column(Float)
    max_drawdown: Mapped[float] = mapped_column(Float)
    stability_score: Mapped[float] = mapped_column(Float)


class StrategyCandidateRecord(StorageBase):
    __tablename__ = "strategy_candidates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    strategy_id: Mapped[str] = mapped_column(String(128), unique=True)
    signal_definition: Mapped[str] = mapped_column(String(128), index=True)
    promotion_status: Mapped[str] = mapped_column(String(32), default="research_only")
    evaluation_metrics: Mapped[str] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ExperimentRunRecord(StorageBase):
    __tablename__ = "experiment_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    experiment_id: Mapped[str] = mapped_column(String(128), unique=True)
    strategy_id: Mapped[str] = mapped_column(String(128), index=True)
    feature_set: Mapped[str] = mapped_column(Text)
    target_definition: Mapped[str] = mapped_column(Text)
    metrics: Mapped[str] = mapped_column(Text)
    promotion_status: Mapped[str] = mapped_column(String(32), default="research_only")
    tracked_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DiscoveryRankingRecord(StorageBase):
    __tablename__ = "discovery_rankings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    strategy_id: Mapped[str] = mapped_column(String(128), index=True)
    alpha_discovery_score: Mapped[float] = mapped_column(Float)
    promotion_status: Mapped[str] = mapped_column(String(32), default="research_only")
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AlphaReportRecord(StorageBase):
    __tablename__ = "alpha_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    report_name: Mapped[str] = mapped_column(String(255), unique=True)
    report_path: Mapped[str] = mapped_column(String(1024))
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())


class StrategyRegistryRecord(StorageBase):
    __tablename__ = "strategy_registry"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    strategy_id: Mapped[str] = mapped_column(String(128), unique=True)
    strategy_name: Mapped[str] = mapped_column(String(255))
    parent_strategy_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(32), index=True)
    creation_source: Mapped[str] = mapped_column(String(64))
    promoted_from: Mapped[str | None] = mapped_column(String(128), nullable=True)
    current_stage: Mapped[str] = mapped_column(String(32))
    features_used: Mapped[str] = mapped_column(Text)
    target_definition: Mapped[str] = mapped_column(Text)
    thresholds: Mapped[str] = mapped_column(Text)
    regime_filters: Mapped[str] = mapped_column(Text)
    risk_rules: Mapped[str] = mapped_column(Text)
    performance_summary: Mapped[str] = mapped_column(Text)


class StrategyVersionRecord(StorageBase):
    __tablename__ = "strategy_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    strategy_id: Mapped[str] = mapped_column(String(128), index=True)
    parent_strategy_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    version: Mapped[int] = mapped_column(Integer)
    changes: Mapped[str] = mapped_column(Text)
    lineage: Mapped[str] = mapped_column(String(128), index=True)


class StrategyHealthRecord(StorageBase):
    __tablename__ = "strategy_health"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    strategy_id: Mapped[str] = mapped_column(String(128), index=True)
    robustness_score: Mapped[float] = mapped_column(Float, default=0.0)
    rolling_sharpe: Mapped[float] = mapped_column(Float, default=0.0)
    rolling_drawdown: Mapped[float] = mapped_column(Float, default=0.0)
    rolling_win_rate: Mapped[float] = mapped_column(Float, default=0.0)
    degradation_score: Mapped[float] = mapped_column(Float, default=0.0)
    degradation_level: Mapped[str] = mapped_column(String(32), default="none")
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DegradationEventRecord(StorageBase):
    __tablename__ = "degradation_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    strategy_id: Mapped[str] = mapped_column(String(128), index=True)
    degradation_score: Mapped[float] = mapped_column(Float)
    degradation_reason: Mapped[str] = mapped_column(String(255))
    degradation_level: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AdaptationCandidateRecord(StorageBase):
    __tablename__ = "adaptation_candidates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    strategy_id: Mapped[str] = mapped_column(String(128), index=True)
    parent_strategy_id: Mapped[str] = mapped_column(String(128), index=True)
    expected_improvement: Mapped[float] = mapped_column(Float)
    adaptation_reason: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PromotionDecisionRecord(StorageBase):
    __tablename__ = "promotion_decisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    strategy_id: Mapped[str] = mapped_column(String(128), index=True)
    previous_status: Mapped[str] = mapped_column(String(32))
    new_status: Mapped[str] = mapped_column(String(32))
    reason: Mapped[str] = mapped_column(String(255))
    metrics_snapshot: Mapped[str] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LifecycleTransitionRecord(StorageBase):
    __tablename__ = "lifecycle_transitions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    strategy_id: Mapped[str] = mapped_column(String(128), index=True)
    previous_status: Mapped[str] = mapped_column(String(32))
    new_status: Mapped[str] = mapped_column(String(32))
    reason: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RegimePerformanceRecord(StorageBase):
    __tablename__ = "regime_performance"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    strategy_id: Mapped[str] = mapped_column(String(128), index=True)
    best_regime: Mapped[str] = mapped_column(String(64))
    worst_regime: Mapped[str] = mapped_column(String(64))
    regime_dependence_score: Mapped[float] = mapped_column(Float)
    performance_by_regime: Mapped[str] = mapped_column(Text)


class RollingMetricRecord(StorageBase):
    __tablename__ = "rolling_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    strategy_id: Mapped[str] = mapped_column(String(128), index=True)
    rolling_sharpe: Mapped[float] = mapped_column(Float, default=0.0)
    rolling_drawdown: Mapped[float] = mapped_column(Float, default=0.0)
    rolling_win_rate: Mapped[float] = mapped_column(Float, default=0.0)
    rolling_profit_factor: Mapped[float] = mapped_column(Float, default=0.0)
    window_count: Mapped[int] = mapped_column(Integer, default=0)


class RobustnessScoreRecord(StorageBase):
    __tablename__ = "robustness_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    strategy_id: Mapped[str] = mapped_column(String(128), index=True)
    robustness_score: Mapped[float] = mapped_column(Float)
    instability_flags: Mapped[str] = mapped_column(String(255))


class FeatureMetadataRecord(StorageBase):
    __tablename__ = "feature_metadata"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    feature_name: Mapped[str] = mapped_column(String(128), unique=True)
    description: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(64))
    feature_version: Mapped[str] = mapped_column(String(32), default="v1")
    owner: Mapped[str] = mapped_column(String(64), default="alphascope")
    tags: Mapped[str] = mapped_column(Text, default="[]")


class FeatureVersionRecord(StorageBase):
    __tablename__ = "feature_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    feature_name: Mapped[str] = mapped_column(String(128), index=True)
    feature_version: Mapped[str] = mapped_column(String(32), index=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    dataset_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    timestamp: Mapped[str] = mapped_column(DateTime(timezone=True), index=True)


class DatasetVersionRecord(StorageBase):
    __tablename__ = "dataset_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dataset_name: Mapped[str] = mapped_column(String(255), index=True)
    dataset_hash: Mapped[str] = mapped_column(String(128), unique=True)
    features_used: Mapped[str] = mapped_column(Text)
    temporal_window: Mapped[str] = mapped_column(Text)
    rows: Mapped[int] = mapped_column(Integer)
    columns: Mapped[str] = mapped_column(Text)


class ModelRegistryRecord(StorageBase):
    __tablename__ = "model_registry"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    model_name: Mapped[str] = mapped_column(String(128), index=True)
    model_version: Mapped[str] = mapped_column(String(64), index=True)
    hyperparameters: Mapped[str] = mapped_column(Text)
    dataset_hash: Mapped[str] = mapped_column(String(128), index=True)
    metrics: Mapped[str] = mapped_column(Text)
    artifact_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    timestamp: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DataLineageRecord(StorageBase):
    __tablename__ = "data_lineage"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dataset_hash: Mapped[str] = mapped_column(String(128), index=True)
    features_used: Mapped[str] = mapped_column(Text)
    model_version: Mapped[str | None] = mapped_column(String(128), nullable=True)
    strategy_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    source: Mapped[str] = mapped_column(String(64))
    timestamp: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())


class BenchmarkRecord(StorageBase):
    __tablename__ = "benchmark_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    benchmark_name: Mapped[str] = mapped_column(String(255), index=True)
    subject_id: Mapped[str] = mapped_column(String(128), index=True)
    benchmark_score: Mapped[float] = mapped_column(Float)
    metrics: Mapped[str] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())


class StrategyMarketplaceRecord(StorageBase):
    __tablename__ = "strategy_marketplace"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    strategy_id: Mapped[str] = mapped_column(String(128), index=True)
    marketplace_score: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(32))
    summary: Mapped[str] = mapped_column(Text)
