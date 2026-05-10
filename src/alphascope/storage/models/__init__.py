"""Official ORM models for AlphaScope storage."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from alphascope.storage.database import Base


class MarketCandle(Base):
    __tablename__ = "market_candles"
    __table_args__ = (UniqueConstraint("timestamp", "symbol", "interval", name="uq_market_candle"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    symbol: Mapped[str] = mapped_column(String(20), index=True)
    interval: Mapped[str] = mapped_column(String(10), index=True)
    open: Mapped[float] = mapped_column(Float)
    high: Mapped[float] = mapped_column(Float)
    low: Mapped[float] = mapped_column(Float)
    close: Mapped[float] = mapped_column(Float)
    volume: Mapped[float] = mapped_column(Float)


class TechnicalFeature(Base):
    __tablename__ = "technical_features"
    __table_args__ = (UniqueConstraint("timestamp", "symbol", "interval", name="uq_technical_feature"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    symbol: Mapped[str] = mapped_column(String(20), index=True)
    interval: Mapped[str] = mapped_column(String(10), index=True)
    close: Mapped[float] = mapped_column(Float)
    return_pct: Mapped[float] = mapped_column(Float)
    ma_short: Mapped[float] = mapped_column(Float)
    ma_long: Mapped[float] = mapped_column(Float)
    rsi: Mapped[float] = mapped_column(Float)
    volatility: Mapped[float] = mapped_column(Float)
    avg_volume: Mapped[float] = mapped_column(Float)
    relative_volume: Mapped[float] = mapped_column(Float)
    momentum: Mapped[float] = mapped_column(Float)
    trend_strength: Mapped[float] = mapped_column(Float)


class AssetRanking(Base):
    __tablename__ = "asset_rankings"
    __table_args__ = (UniqueConstraint("timestamp", "symbol", "interval", name="uq_asset_ranking"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    symbol: Mapped[str] = mapped_column(String(20), index=True)
    interval: Mapped[str] = mapped_column(String(10), index=True)

    score: Mapped[float] = mapped_column(Float)
    rank: Mapped[int] = mapped_column(Integer)

    heuristic_score: Mapped[float] = mapped_column(Float, default=0.0)
    ml_probability: Mapped[float] = mapped_column(Float, default=0.0)
    news_score: Mapped[float] = mapped_column(Float, default=0.0)
    market_sentiment_adjustment: Mapped[float] = mapped_column(Float, default=0.0)

    momentum_component: Mapped[float] = mapped_column(Float, default=0.0)
    volume_component: Mapped[float] = mapped_column(Float, default=0.0)
    trend_component: Mapped[float] = mapped_column(Float, default=0.0)
    rsi_component: Mapped[float] = mapped_column(Float, default=0.0)
    technical_score: Mapped[float] = mapped_column(Float, default=0.0)
    trend_score: Mapped[float] = mapped_column(Float, default=0.0)
    volatility_score: Mapped[float] = mapped_column(Float, default=0.0)
    volume_score: Mapped[float] = mapped_column(Float, default=0.0)
    risk_score: Mapped[float] = mapped_column(Float, default=0.0)
    regime_score: Mapped[float] = mapped_column(Float, default=0.0)
    market_regime: Mapped[str] = mapped_column(String(16), default="sideways")


class PaperTrade(Base):
    __tablename__ = "paper_trades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    symbol: Mapped[str] = mapped_column(String(20), index=True)
    side: Mapped[str] = mapped_column(String(10))
    quantity: Mapped[float] = mapped_column(Float)
    price: Mapped[float] = mapped_column(Float)
    fee: Mapped[float] = mapped_column(Float)
    realized_pnl: Mapped[float] = mapped_column(Float, default=0.0)


class PortfolioSnapshot(Base):
    __tablename__ = "portfolio_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    cash: Mapped[float] = mapped_column(Float)
    equity: Mapped[float] = mapped_column(Float)
    realized_pnl: Mapped[float] = mapped_column(Float)
    unrealized_pnl: Mapped[float] = mapped_column(Float)
    positions_json: Mapped[str] = mapped_column(String)


class TradeExecution(Base):
    __tablename__ = "trade_executions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    symbol: Mapped[str] = mapped_column(String(20), index=True)
    side: Mapped[str] = mapped_column(String(10), index=True)
    quantity: Mapped[float] = mapped_column(Float)
    entry_price: Mapped[float] = mapped_column(Float)
    exit_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    stop_loss_price: Mapped[float] = mapped_column(Float)
    take_profit_price: Mapped[float] = mapped_column(Float)
    pnl: Mapped[float] = mapped_column(Float, default=0.0)
    pnl_pct: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(32), index=True)
    order_id: Mapped[str] = mapped_column(String(128), index=True)
    source: Mapped[str] = mapped_column(String(32), default="alphascope")
    mode: Mapped[str] = mapped_column(String(32), default="testnet")
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    notes: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class OpenPosition(Base):
    __tablename__ = "open_positions"
    __table_args__ = (UniqueConstraint("symbol", name="uq_open_position_symbol"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(20), index=True)
    quantity: Mapped[float] = mapped_column(Float)
    entry_price: Mapped[float] = mapped_column(Float)
    current_price: Mapped[float] = mapped_column(Float)
    unrealized_pnl: Mapped[float] = mapped_column(Float, default=0.0)
    stop_price: Mapped[float] = mapped_column(Float)
    take_profit_price: Mapped[float] = mapped_column(Float)
    trailing_stop_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    order_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    mode: Mapped[str] = mapped_column(String(32), default="testnet")
    status: Mapped[str] = mapped_column(String(32), default="OPEN")
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class RiskEvent(Base):
    __tablename__ = "risk_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    symbol: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    severity: Mapped[str] = mapped_column(String(32), default="warning")
    decision: Mapped[str] = mapped_column(String(32))
    reason: Mapped[str] = mapped_column(String(512))
    payload_json: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class DailyPerformance(Base):
    __tablename__ = "daily_performance"
    __table_args__ = (UniqueConstraint("date", name="uq_daily_performance_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[date] = mapped_column(index=True)
    total_trades: Mapped[int] = mapped_column(Integer, default=0)
    wins: Mapped[int] = mapped_column(Integer, default=0)
    losses: Mapped[int] = mapped_column(Integer, default=0)
    win_rate: Mapped[float] = mapped_column(Float, default=0.0)
    realized_pnl: Mapped[float] = mapped_column(Float, default=0.0)
    realized_pnl_pct: Mapped[float] = mapped_column(Float, default=0.0)
    max_drawdown: Mapped[float] = mapped_column(Float, default=0.0)
    open_positions: Mapped[int] = mapped_column(Integer, default=0)
    consecutive_losses: Mapped[int] = mapped_column(Integer, default=0)
    paused: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class AccountSnapshot(Base):
    __tablename__ = "account_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    mode: Mapped[str] = mapped_column(String(32), default="testnet")
    total_balance: Mapped[float] = mapped_column(Float)
    free_balance: Mapped[float] = mapped_column(Float)
    locked_balance: Mapped[float] = mapped_column(Float, default=0.0)
    exposure_pct: Mapped[float] = mapped_column(Float, default=0.0)
    open_positions: Mapped[int] = mapped_column(Integer, default=0)
    open_orders: Mapped[int] = mapped_column(Integer, default=0)
    snapshot_json: Mapped[str] = mapped_column(String)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    action: Mapped[str] = mapped_column(String(64), index=True)
    actor: Mapped[str] = mapped_column(String(64), index=True)
    source: Mapped[str] = mapped_column(String(64), index=True)
    target: Mapped[str] = mapped_column(String(128), index=True)
    payload_json: Mapped[str] = mapped_column(String)


class RankingCycle(Base):
    __tablename__ = "ranking_cycles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    interval: Mapped[str] = mapped_column(String(10), index=True)
    cycle_id: Mapped[str] = mapped_column(String(64), index=True)
    top_symbol: Mapped[str] = mapped_column(String(20), index=True)
    top_score: Mapped[float] = mapped_column(Float)
    market_regime: Mapped[str] = mapped_column(String(16), default="sideways")
    payload_json: Mapped[str] = mapped_column(String)


class TradeHistory(Base):
    __tablename__ = "trade_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trade_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    order_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    symbol: Mapped[str] = mapped_column(String(20), index=True)
    timeframe: Mapped[str] = mapped_column(String(10), default="1h", index=True)
    side: Mapped[str] = mapped_column(String(10), default="BUY")
    mode: Mapped[str] = mapped_column(String(32), default="paper", index=True)
    status: Mapped[str] = mapped_column(String(32), default="OPEN", index=True)
    entry_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    exit_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    entry_price: Mapped[float] = mapped_column(Float)
    exit_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    quantity: Mapped[float] = mapped_column(Float, default=0.0)
    order_size_usdt: Mapped[float] = mapped_column(Float, default=0.0)
    fees_paid: Mapped[float] = mapped_column(Float, default=0.0)
    pnl: Mapped[float] = mapped_column(Float, default=0.0)
    pnl_percent: Mapped[float] = mapped_column(Float, default=0.0)
    ranking_score: Mapped[float] = mapped_column(Float, default=0.0)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    ml_score: Mapped[float] = mapped_column(Float, default=0.0)
    heuristic_score: Mapped[float] = mapped_column(Float, default=0.0)
    news_score: Mapped[float] = mapped_column(Float, default=0.0)
    sentiment_score: Mapped[float] = mapped_column(Float, default=0.0)
    fear_greed_score: Mapped[float] = mapped_column(Float, default=0.0)
    volatility: Mapped[float] = mapped_column(Float, default=0.0)
    volume_ratio: Mapped[float] = mapped_column(Float, default=0.0)
    trend_direction: Mapped[str] = mapped_column(String(32), default="unknown")
    reason_opened: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reason_closed: Mapped[str | None] = mapped_column(String(255), nullable=True)
    holding_minutes: Mapped[float] = mapped_column(Float, default=0.0)
    was_successful: Mapped[bool] = mapped_column(Boolean, default=False)
    prediction_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    stop_loss_hit: Mapped[bool] = mapped_column(Boolean, default=False)
    take_profit_hit: Mapped[bool] = mapped_column(Boolean, default=False)
    trailing_stop_hit: Mapped[bool] = mapped_column(Boolean, default=False)
    max_drawdown_during_trade: Mapped[float] = mapped_column(Float, default=0.0)
    max_profit_during_trade: Mapped[float] = mapped_column(Float, default=0.0)
    trade_duration_minutes: Mapped[float] = mapped_column(Float, default=0.0)
    decision_quality_score: Mapped[float] = mapped_column(Float, default=5.0)
    decision_quality_label: Mapped[str] = mapped_column(String(32), default="neutral")
    trailing_stop_armed: Mapped[bool] = mapped_column(Boolean, default=False)
    notes_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class ModelPrediction(Base):
    __tablename__ = "model_predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    symbol: Mapped[str] = mapped_column(String(20), index=True)
    timeframe: Mapped[str] = mapped_column(String(10), default="1h", index=True)
    model_name: Mapped[str] = mapped_column(String(128), index=True)
    model_version: Mapped[str] = mapped_column(String(64), default="unknown", index=True)
    prediction_score: Mapped[float] = mapped_column(Float, default=0.0)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    buy_probability: Mapped[float] = mapped_column(Float, default=0.0)
    sell_probability: Mapped[float] = mapped_column(Float, default=0.0)
    hold_probability: Mapped[float] = mapped_column(Float, default=0.0)
    predicted_label: Mapped[str] = mapped_column(String(16), default="hold")
    ranking_score: Mapped[float] = mapped_column(Float, default=0.0)
    heuristic_score: Mapped[float] = mapped_column(Float, default=0.0)
    news_score: Mapped[float] = mapped_column(Float, default=0.0)
    features_json: Mapped[str] = mapped_column(Text, default="{}")


class MarketSnapshot(Base):
    __tablename__ = "market_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    symbol: Mapped[str] = mapped_column(String(20), index=True)
    timeframe: Mapped[str] = mapped_column(String(10), default="1h", index=True)
    current_price: Mapped[float] = mapped_column(Float, default=0.0)
    price_change_1h: Mapped[float] = mapped_column(Float, default=0.0)
    price_change_24h: Mapped[float] = mapped_column(Float, default=0.0)
    volume: Mapped[float] = mapped_column(Float, default=0.0)
    relative_volume: Mapped[float] = mapped_column(Float, default=0.0)
    volatility: Mapped[float] = mapped_column(Float, default=0.0)
    rsi: Mapped[float] = mapped_column(Float, default=0.0)
    macd: Mapped[float] = mapped_column(Float, default=0.0)
    bollinger_upper: Mapped[float] = mapped_column(Float, default=0.0)
    bollinger_lower: Mapped[float] = mapped_column(Float, default=0.0)
    sma20: Mapped[float] = mapped_column(Float, default=0.0)
    sma50: Mapped[float] = mapped_column(Float, default=0.0)
    ema9: Mapped[float] = mapped_column(Float, default=0.0)
    ema21: Mapped[float] = mapped_column(Float, default=0.0)
    atr: Mapped[float] = mapped_column(Float, default=0.0)
    news_score: Mapped[float] = mapped_column(Float, default=0.0)
    fear_greed_score: Mapped[float] = mapped_column(Float, default=0.0)
    ranking_score: Mapped[float] = mapped_column(Float, default=0.0)
    ml_score: Mapped[float] = mapped_column(Float, default=0.0)
    heuristic_score: Mapped[float] = mapped_column(Float, default=0.0)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    current_position: Mapped[float] = mapped_column(Float, default=0.0)
    available_balance: Mapped[float] = mapped_column(Float, default=0.0)
    total_equity: Mapped[float] = mapped_column(Float, default=0.0)
    market_cap: Mapped[float] = mapped_column(Float, default=0.0)
    btc_dominance: Mapped[float] = mapped_column(Float, default=0.0)
    sentiment_score: Mapped[float] = mapped_column(Float, default=0.0)
    snapshot_json: Mapped[str] = mapped_column(Text, default="{}")


class FeatureSnapshot(Base):
    __tablename__ = "feature_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    symbol: Mapped[str] = mapped_column(String(20), index=True)
    timeframe: Mapped[str] = mapped_column(String(10), default="1h", index=True)
    feature_version: Mapped[str] = mapped_column(String(32), default="v1")
    features_json: Mapped[str] = mapped_column(Text, default="{}")


class RetrainingRun(Base):
    __tablename__ = "retraining_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default="started", index=True)
    trigger_reason: Mapped[str] = mapped_column(String(255), default="manual")
    cycle_count: Mapped[int] = mapped_column(Integer, default=0)
    trade_count: Mapped[int] = mapped_column(Integer, default=0)
    win_rate_before: Mapped[float] = mapped_column(Float, default=0.0)
    drawdown_before: Mapped[float] = mapped_column(Float, default=0.0)
    model_score_before: Mapped[float] = mapped_column(Float, default=0.0)
    selected_model_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    selected_model_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    candidate_count: Mapped[int] = mapped_column(Integer, default=0)
    promoted: Mapped[bool] = mapped_column(Boolean, default=False)
    rollback_triggered: Mapped[bool] = mapped_column(Boolean, default=False)
    metrics_json: Mapped[str] = mapped_column(Text, default="{}")
    notes_json: Mapped[str] = mapped_column(Text, default="{}")


class LiveTradeFeedback(Base):
    __tablename__ = "live_trade_feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trade_id: Mapped[str] = mapped_column(String(128), index=True)
    symbol: Mapped[str] = mapped_column(String(20), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    quality_score: Mapped[float] = mapped_column(Float, default=5.0)
    quality_label: Mapped[str] = mapped_column(String(32), default="neutral")
    prediction_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    ranking_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    timing_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    stop_too_tight: Mapped[bool] = mapped_column(Boolean, default=False)
    take_profit_too_low: Mapped[bool] = mapped_column(Boolean, default=False)
    could_have_earned_more: Mapped[bool] = mapped_column(Boolean, default=False)
    feedback_json: Mapped[str] = mapped_column(Text, default="{}")


class ModelVersion(Base):
    __tablename__ = "model_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    model_name: Mapped[str] = mapped_column(String(128), index=True)
    version: Mapped[str] = mapped_column(String(64), index=True)
    stage: Mapped[str] = mapped_column(String(32), default="experiments", index=True)
    status: Mapped[str] = mapped_column(String(32), default="candidate", index=True)
    trained_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    promoted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    artifact_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    metadata_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    dataset_used: Mapped[str | None] = mapped_column(String(255), nullable=True)
    features_used: Mapped[str] = mapped_column(Text, default="[]")
    average_score: Mapped[float] = mapped_column(Float, default=0.0)
    trade_count: Mapped[int] = mapped_column(Integer, default=0)
    candle_count: Mapped[int] = mapped_column(Integer, default=0)
    metrics_json: Mapped[str] = mapped_column(Text, default="{}")
    params_json: Mapped[str] = mapped_column(Text, default="{}")
    rollback_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)


class RankingHistory(Base):
    __tablename__ = "ranking_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cycle_id: Mapped[str] = mapped_column(String(64), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    symbol: Mapped[str] = mapped_column(String(20), index=True)
    timeframe: Mapped[str] = mapped_column(String(10), default="1h", index=True)
    rank: Mapped[int] = mapped_column(Integer)
    ranking_score: Mapped[float] = mapped_column(Float, default=0.0)
    heuristic_score: Mapped[float] = mapped_column(Float, default=0.0)
    ml_score: Mapped[float] = mapped_column(Float, default=0.0)
    news_score: Mapped[float] = mapped_column(Float, default=0.0)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    payload_json: Mapped[str] = mapped_column(Text, default="{}")


class SignalHistory(Base):
    __tablename__ = "signal_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    symbol: Mapped[str] = mapped_column(String(20), index=True)
    timeframe: Mapped[str] = mapped_column(String(10), default="1h", index=True)
    signal_type: Mapped[str] = mapped_column(String(32), index=True)
    signal_strength: Mapped[float] = mapped_column(Float, default=0.0)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    ranking_score: Mapped[float] = mapped_column(Float, default=0.0)
    payload_json: Mapped[str] = mapped_column(Text, default="{}")


class PortfolioAnalyticsSnapshot(Base):
    __tablename__ = "portfolio_analytics_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    mode: Mapped[str] = mapped_column(String(32), default="paper", index=True)
    total_equity: Mapped[float] = mapped_column(Float, default=0.0)
    available_balance: Mapped[float] = mapped_column(Float, default=0.0)
    drawdown: Mapped[float] = mapped_column(Float, default=0.0)
    sharpe_ratio: Mapped[float] = mapped_column(Float, default=0.0)
    profit_factor: Mapped[float] = mapped_column(Float, default=0.0)
    win_rate: Mapped[float] = mapped_column(Float, default=0.0)
    open_trades: Mapped[int] = mapped_column(Integer, default=0)
    closed_trades: Mapped[int] = mapped_column(Integer, default=0)
    payload_json: Mapped[str] = mapped_column(Text, default="{}")


__all__ = [
    "AccountSnapshot",
    "AuditEvent",
    "AssetRanking",
    "DailyPerformance",
    "MarketCandle",
    "OpenPosition",
    "PaperTrade",
    "PortfolioAnalyticsSnapshot",
    "PortfolioSnapshot",
    "RankingCycle",
    "RankingHistory",
    "RetrainingRun",
    "RiskEvent",
    "SignalHistory",
    "TechnicalFeature",
    "TradeHistory",
    "TradeExecution",
    "FeatureSnapshot",
    "LiveTradeFeedback",
    "MarketSnapshot",
    "ModelPrediction",
    "ModelVersion",
]
