"""Repositories for persistence and retrieval."""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from datetime import date, datetime
from uuid import uuid4

import pandas as pd
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from alphascope.core.exceptions import StorageError
from alphascope.storage.database import SessionLocal, engine, session_scope
from alphascope.storage.models import (
    AccountSnapshot,
    AuditEvent,
    AssetRanking,
    DailyPerformance,
    FeatureSnapshot,
    LiveTradeFeedback,
    MarketCandle,
    MarketSnapshot,
    ModelPrediction,
    ModelVersion,
    OpenPosition,
    PaperTrade,
    PortfolioAnalyticsSnapshot,
    PortfolioSnapshot,
    RankingCycle,
    RankingHistory,
    RetrainingRun,
    RiskEvent,
    SignalHistory,
    TechnicalFeature,
    TradeHistory,
    TradeExecution,
)
from alphascope.utils.time import ensure_utc, normalize_datetime_columns, safe_utc_diff, utc_now


class StorageRepository:
    """Persistence facade for AlphaScope datasets."""

    INVALID_POSITION_STATUSES = {"closed", "sold", "cancelled", "canceled"}
    DATETIME_FIELDS = {
        "timestamp",
        "opened_at",
        "updated_at",
        "created_at",
        "entry_time",
        "exit_time",
        "trained_at",
        "promoted_at",
        "started_at",
        "finished_at",
        "checked_at",
        "recorded_at",
        "saved_at",
    }
    FRAME_DATETIME_FIELDS = ["timestamp", "opened_at", "updated_at", "created_at", "entry_time", "exit_time"]
    logger = logging.getLogger(__name__)

    def __init__(self, *, auto_cleanup: bool = True) -> None:
        if auto_cleanup:
            self.cleanup_persisted_positions()

    @staticmethod
    def _dialect_name(session) -> str:
        bind = getattr(session, "bind", None)
        dialect = getattr(bind, "dialect", None)
        if dialect is not None and getattr(dialect, "name", None):
            return str(dialect.name)
        return engine.dialect.name

    def _bulk_upsert_records(
        self,
        *,
        session,
        model,
        records: list[dict[str, object]],
        conflict_columns: list[str],
        update_columns: list[str],
    ) -> None:
        if not records:
            return
        normalized = [self._normalize_record_datetimes(record) for record in records]
        dialect_name = self._dialect_name(session)
        update_mapping: dict[str, object] = {}
        if dialect_name == "sqlite":
            statement = sqlite_insert(model).values(normalized)
            update_mapping = {
                column: getattr(statement.excluded, column)
                for column in update_columns
                if column not in conflict_columns
            }
            session.execute(statement.on_conflict_do_update(index_elements=conflict_columns, set_=update_mapping))
            return
        if dialect_name == "postgresql":
            statement = postgresql_insert(model).values(normalized)
            update_mapping = {
                column: getattr(statement.excluded, column)
                for column in update_columns
                if column not in conflict_columns
            }
            session.execute(statement.on_conflict_do_update(index_elements=conflict_columns, set_=update_mapping))
            return
        for record in normalized:
            session.merge(model(**record))

    def save_candles(self, candles: pd.DataFrame) -> int:
        if candles.empty:
            return 0
        records = candles.to_dict(orient="records")
        with session_scope() as session:
            self._bulk_upsert_records(
                session=session,
                model=MarketCandle,
                records=records,
                conflict_columns=["timestamp", "symbol", "interval"],
                update_columns=["timestamp", "symbol", "interval", "open", "high", "low", "close", "volume"],
            )
        return len(records)

    def get_candles(self, symbol: str, interval: str, limit: int | None = None) -> pd.DataFrame:
        with SessionLocal() as session:
            query = (
                select(MarketCandle)
                .where(MarketCandle.symbol == symbol, MarketCandle.interval == interval)
                .order_by(MarketCandle.timestamp.asc())
            )
            rows = session.execute(query).scalars().all()
        data = [self._to_dict(row) for row in rows]
        frame = pd.DataFrame(data)
        if frame.empty:
            return frame
        if limit is not None:
            frame = frame.tail(limit)
        return frame.reset_index(drop=True)

    def save_features(self, features: pd.DataFrame) -> int:
        if features.empty:
            return 0
        records = features.to_dict(orient="records")
        with session_scope() as session:
            self._bulk_upsert_records(
                session=session,
                model=TechnicalFeature,
                records=records,
                conflict_columns=["timestamp", "symbol", "interval"],
                update_columns=[
                    "timestamp",
                    "symbol",
                    "interval",
                    "close",
                    "return_pct",
                    "ma_short",
                    "ma_long",
                    "rsi",
                    "volatility",
                    "avg_volume",
                    "relative_volume",
                    "momentum",
                    "trend_strength",
                ],
            )
        return len(records)

    def get_features(self, symbol: str, interval: str) -> pd.DataFrame:
        with SessionLocal() as session:
            query = (
                select(TechnicalFeature)
                .where(TechnicalFeature.symbol == symbol, TechnicalFeature.interval == interval)
                .order_by(TechnicalFeature.timestamp.asc())
            )
            rows = session.execute(query).scalars().all()
        return pd.DataFrame([self._to_dict(row) for row in rows])

    def save_ranking(self, rankings: pd.DataFrame, interval: str) -> int:
        if rankings.empty:
            return 0
        records = [self._normalize_ranking_record(record) for record in rankings.to_dict(orient="records")]
        timestamp = records[0]["timestamp"]
        ranking_columns = sorted({key for record in records for key in record.keys()} | {"interval"})
        ranking_records = []
        for record in records:
            payload = {column: record.get(column) for column in ranking_columns if column != "interval"}
            payload["interval"] = interval
            ranking_records.append(payload)
        with session_scope() as session:
            self._bulk_upsert_records(
                session=session,
                model=AssetRanking,
                records=ranking_records,
                conflict_columns=["timestamp", "symbol", "interval"],
                update_columns=ranking_columns,
            )
            top_record = min(records, key=lambda item: int(item.get("rank", 999999)))
            session.add(
                RankingCycle(
                    timestamp=timestamp,
                    interval=interval,
                    cycle_id=f"{interval}:{pd.Timestamp(timestamp).isoformat()}",
                    top_symbol=str(top_record["symbol"]),
                    top_score=float(top_record["score"]),
                    market_regime=str(top_record.get("market_regime", "sideways")),
                    payload_json=json.dumps(records, default=str),
                )
            )
        return len(records)

    def get_latest_ranking(self, interval: str) -> pd.DataFrame:
        with SessionLocal() as session:
            latest_timestamp = session.execute(
                select(AssetRanking.timestamp).where(AssetRanking.interval == interval).order_by(AssetRanking.timestamp.desc())
            ).scalars().first()
            if latest_timestamp is None:
                return pd.DataFrame()
            rows = session.execute(
                select(AssetRanking)
                .where(AssetRanking.interval == interval, AssetRanking.timestamp == latest_timestamp)
                .order_by(AssetRanking.rank.asc())
            ).scalars().all()
        return pd.DataFrame([self._to_dict(row) for row in rows])

    def save_trades(self, trades: list[dict[str, object]]) -> int:
        if not trades:
            return 0
        with session_scope() as session:
            for trade in trades:
                session.add(PaperTrade(**trade))
        return len(trades)

    def save_snapshot(self, snapshot: dict[str, object]) -> int:
        with session_scope() as session:
            payload = snapshot.copy()
            payload["positions_json"] = json.dumps(payload["positions_json"])
            session.add(PortfolioSnapshot(**payload))
        return 1

    def save_snapshots(self, snapshots: list[dict[str, object]]) -> int:
        saved = 0
        for snapshot in snapshots:
            saved += self.save_snapshot(snapshot)
        return saved

    def get_latest_snapshot(self) -> dict[str, object] | None:
        with SessionLocal() as session:
            row = session.execute(
                select(PortfolioSnapshot).order_by(PortfolioSnapshot.timestamp.desc())
            ).scalars().first()
        if row is None:
            return None
        payload = self._to_dict(row)
        payload["positions_json"] = json.loads(str(payload["positions_json"]))
        return payload

    def save_trade_execution(self, trade: dict[str, object]) -> int:
        with session_scope() as session:
            session.add(TradeExecution(**self._normalize_record_datetimes(trade)))
        return 1

    def update_trade_execution(self, order_id: str, updates: dict[str, object]) -> int:
        with session_scope() as session:
            row = session.execute(select(TradeExecution).where(TradeExecution.order_id == order_id)).scalars().first()
            if row is None:
                raise StorageError(f"TradeExecution not found for order_id={order_id}")
            for key, value in updates.items():
                setattr(row, key, value)
        return 1

    def get_trade_executions(self, *, mode: str | None = None, status: str | None = None, limit: int | None = None) -> pd.DataFrame:
        with SessionLocal() as session:
            query = select(TradeExecution).order_by(TradeExecution.timestamp.desc())
            if mode:
                query = query.where(TradeExecution.mode == mode)
            if status:
                query = query.where(TradeExecution.status == status)
            rows = session.execute(query).scalars().all()
        frame = pd.DataFrame([self._to_dict(row) for row in rows])
        if limit is not None and not frame.empty:
            frame = frame.head(limit)
        return frame

    def upsert_open_position(self, position: dict[str, object]) -> int:
        position = self._normalize_record_datetimes(position)
        if not self.is_valid_open_position(position):
            symbol = str(position.get("symbol", "")).upper()
            if symbol:
                self.close_open_position(symbol, reason="invalid_position_rejected")
            return 0
        symbol = str(position["symbol"]).upper()
        with session_scope() as session:
            row = session.execute(select(OpenPosition).where(OpenPosition.symbol == symbol)).scalars().first()
            if row is None:
                session.add(OpenPosition(**position))
            else:
                for key, value in position.items():
                    setattr(row, key, value)
        return 1

    def close_open_position(self, symbol: str, *, reason: str = "position_closed") -> int:
        with session_scope() as session:
            session.execute(delete(OpenPosition).where(OpenPosition.symbol == symbol.upper()))
        self.reconcile_trade_execution(symbol=symbol, reason=reason)
        return 1

    def get_open_positions(self) -> pd.DataFrame:
        with SessionLocal() as session:
            rows = session.execute(select(OpenPosition).order_by(OpenPosition.opened_at.asc())).scalars().all()
        frame = pd.DataFrame([self._to_dict(row) for row in rows])
        frame = normalize_datetime_columns(frame, self.FRAME_DATETIME_FIELDS)
        return self._sanitize_open_positions_frame(frame)

    def get_open_position(self, symbol: str) -> dict[str, object] | None:
        with SessionLocal() as session:
            row = session.execute(select(OpenPosition).where(OpenPosition.symbol == symbol.upper())).scalars().first()
        if row is None:
            return None
        payload = self._to_dict(row)
        if self.is_valid_open_position(payload):
            return payload
        self.close_open_position(str(payload.get("symbol", symbol)).upper(), reason="invalid_position_removed")
        return None

    def save_risk_event(self, event: dict[str, object]) -> int:
        with session_scope() as session:
            payload = event.copy()
            payload["payload_json"] = json.dumps(payload.get("payload_json", {}), default=str)
            session.add(RiskEvent(**payload))
        return 1

    def get_risk_events(self, limit: int | None = None) -> pd.DataFrame:
        with SessionLocal() as session:
            rows = session.execute(select(RiskEvent).order_by(RiskEvent.timestamp.desc())).scalars().all()
        frame = pd.DataFrame([self._deserialize_risk_event(row) for row in rows])
        if limit is not None and not frame.empty:
            frame = frame.head(limit)
        return frame

    def save_account_snapshot(self, snapshot: dict[str, object]) -> int:
        with session_scope() as session:
            payload = self._normalize_record_datetimes(snapshot)
            payload["snapshot_json"] = json.dumps(payload.get("snapshot_json", {}), default=str)
            session.add(AccountSnapshot(**payload))
        return 1

    def save_market_snapshots(self, snapshots: list[dict[str, object]]) -> int:
        if not snapshots:
            return 0
        with session_scope() as session:
            for snapshot in snapshots:
                payload = snapshot.copy()
                payload["snapshot_json"] = json.dumps(payload.get("snapshot_json", {}), default=str)
                session.add(MarketSnapshot(**payload))
        return len(snapshots)

    def get_market_snapshots(self, *, symbol: str | None = None, timeframe: str | None = None, limit: int | None = None) -> pd.DataFrame:
        with SessionLocal() as session:
            query = select(MarketSnapshot).order_by(MarketSnapshot.timestamp.desc())
            if symbol:
                query = query.where(MarketSnapshot.symbol == symbol.upper())
            if timeframe:
                query = query.where(MarketSnapshot.timeframe == timeframe)
            rows = session.execute(query).scalars().all()
        frame = pd.DataFrame([self._deserialize_json_field(row, "snapshot_json") for row in rows])
        if limit is not None and not frame.empty:
            frame = frame.head(limit)
        return frame

    def save_feature_snapshots(self, snapshots: list[dict[str, object]]) -> int:
        if not snapshots:
            return 0
        with session_scope() as session:
            for snapshot in snapshots:
                payload = snapshot.copy()
                payload["features_json"] = json.dumps(payload.get("features_json", {}), default=str)
                session.add(FeatureSnapshot(**payload))
        return len(snapshots)

    def get_feature_snapshots(self, *, symbol: str | None = None, timeframe: str | None = None, limit: int | None = None) -> pd.DataFrame:
        with SessionLocal() as session:
            query = select(FeatureSnapshot).order_by(FeatureSnapshot.timestamp.desc())
            if symbol:
                query = query.where(FeatureSnapshot.symbol == symbol.upper())
            if timeframe:
                query = query.where(FeatureSnapshot.timeframe == timeframe)
            rows = session.execute(query).scalars().all()
        frame = pd.DataFrame([self._deserialize_json_field(row, "features_json") for row in rows])
        if limit is not None and not frame.empty:
            frame = frame.head(limit)
        return frame

    def save_model_predictions(self, predictions: list[dict[str, object]]) -> int:
        if not predictions:
            return 0
        with session_scope() as session:
            for prediction in predictions:
                payload = prediction.copy()
                payload["features_json"] = json.dumps(payload.get("features_json", {}), default=str)
                session.add(ModelPrediction(**payload))
        return len(predictions)

    def get_model_predictions(self, *, symbol: str | None = None, timeframe: str | None = None, limit: int | None = None) -> pd.DataFrame:
        with SessionLocal() as session:
            query = select(ModelPrediction).order_by(ModelPrediction.timestamp.desc())
            if symbol:
                query = query.where(ModelPrediction.symbol == symbol.upper())
            if timeframe:
                query = query.where(ModelPrediction.timeframe == timeframe)
            rows = session.execute(query).scalars().all()
        frame = pd.DataFrame([self._deserialize_json_field(row, "features_json") for row in rows])
        if limit is not None and not frame.empty:
            frame = frame.head(limit)
        return frame

    def save_ranking_history(self, rows: list[dict[str, object]]) -> int:
        if not rows:
            return 0
        with session_scope() as session:
            for row in rows:
                payload = row.copy()
                payload["payload_json"] = json.dumps(payload.get("payload_json", {}), default=str)
                session.add(RankingHistory(**payload))
        return len(rows)

    def get_ranking_history(self, *, timeframe: str | None = None, limit: int | None = None) -> pd.DataFrame:
        with SessionLocal() as session:
            query = select(RankingHistory).order_by(RankingHistory.timestamp.desc(), RankingHistory.rank.asc())
            if timeframe:
                query = query.where(RankingHistory.timeframe == timeframe)
            rows = session.execute(query).scalars().all()
        frame = pd.DataFrame([self._deserialize_json_field(row, "payload_json") for row in rows])
        if limit is not None and not frame.empty:
            frame = frame.head(limit)
        return frame

    def save_signal_history(self, rows: list[dict[str, object]]) -> int:
        if not rows:
            return 0
        with session_scope() as session:
            for row in rows:
                payload = row.copy()
                payload["payload_json"] = json.dumps(payload.get("payload_json", {}), default=str)
                session.add(SignalHistory(**payload))
        return len(rows)

    def get_signal_history(self, *, signal_type: str | None = None, limit: int | None = None) -> pd.DataFrame:
        with SessionLocal() as session:
            query = select(SignalHistory).order_by(SignalHistory.timestamp.desc())
            if signal_type:
                query = query.where(SignalHistory.signal_type == signal_type)
            rows = session.execute(query).scalars().all()
        frame = pd.DataFrame([self._deserialize_json_field(row, "payload_json") for row in rows])
        if limit is not None and not frame.empty:
            frame = frame.head(limit)
        return frame

    def save_portfolio_analytics_snapshot(self, snapshot: dict[str, object]) -> int:
        with session_scope() as session:
            payload = snapshot.copy()
            payload["payload_json"] = json.dumps(payload.get("payload_json", {}), default=str)
            session.add(PortfolioAnalyticsSnapshot(**payload))
        return 1

    def get_portfolio_analytics_snapshots(self, *, limit: int | None = None) -> pd.DataFrame:
        with SessionLocal() as session:
            rows = session.execute(select(PortfolioAnalyticsSnapshot).order_by(PortfolioAnalyticsSnapshot.timestamp.desc())).scalars().all()
        frame = pd.DataFrame([self._deserialize_json_field(row, "payload_json") for row in rows])
        if limit is not None and not frame.empty:
            frame = frame.head(limit)
        return frame

    def save_model_version(self, payload: dict[str, object]) -> int:
        with session_scope() as session:
            record = payload.copy()
            record["features_used"] = json.dumps(record.get("features_used", []), default=str)
            record["metrics_json"] = json.dumps(record.get("metrics_json", {}), default=str)
            record["params_json"] = json.dumps(record.get("params_json", {}), default=str)
            session.add(ModelVersion(**record))
        return 1

    def get_model_versions(self, *, model_name: str | None = None, stage: str | None = None, limit: int | None = None) -> pd.DataFrame:
        with SessionLocal() as session:
            query = select(ModelVersion).order_by(ModelVersion.trained_at.desc())
            if model_name:
                query = query.where(ModelVersion.model_name == model_name)
            if stage:
                query = query.where(ModelVersion.stage == stage)
            rows = session.execute(query).scalars().all()
        frame = pd.DataFrame([self._deserialize_model_version(row) for row in rows])
        if limit is not None and not frame.empty:
            frame = frame.head(limit)
        return frame

    def save_retraining_run(self, payload: dict[str, object]) -> int:
        with session_scope() as session:
            record = payload.copy()
            record["metrics_json"] = json.dumps(record.get("metrics_json", {}), default=str)
            record["notes_json"] = json.dumps(record.get("notes_json", {}), default=str)
            session.add(RetrainingRun(**record))
        return 1

    def update_retraining_run(self, run_id: str, updates: dict[str, object]) -> int:
        with session_scope() as session:
            row = session.execute(select(RetrainingRun).where(RetrainingRun.run_id == run_id)).scalars().first()
            if row is None:
                raise StorageError(f"RetrainingRun not found for run_id={run_id}")
            for key, value in updates.items():
                if key in {"metrics_json", "notes_json"}:
                    setattr(row, key, json.dumps(value, default=str))
                else:
                    setattr(row, key, value)
        return 1

    def get_retraining_runs(self, *, limit: int | None = None) -> pd.DataFrame:
        with SessionLocal() as session:
            rows = session.execute(select(RetrainingRun).order_by(RetrainingRun.started_at.desc())).scalars().all()
        frame = pd.DataFrame([self._deserialize_retraining_run(row) for row in rows])
        if limit is not None and not frame.empty:
            frame = frame.head(limit)
        return frame

    def save_live_trade_feedback(self, payload: dict[str, object]) -> int:
        with session_scope() as session:
            record = payload.copy()
            record["feedback_json"] = json.dumps(record.get("feedback_json", {}), default=str)
            session.add(LiveTradeFeedback(**record))
        return 1

    def get_live_trade_feedback(self, *, limit: int | None = None) -> pd.DataFrame:
        with SessionLocal() as session:
            rows = session.execute(select(LiveTradeFeedback).order_by(LiveTradeFeedback.timestamp.desc())).scalars().all()
        frame = pd.DataFrame([self._deserialize_json_field(row, "feedback_json") for row in rows])
        if limit is not None and not frame.empty:
            frame = frame.head(limit)
        return frame

    def open_trade_history(self, payload: dict[str, object]) -> str:
        record = payload.copy()
        trade_id = str(record.get("trade_id") or record.get("order_id") or f"trade_{uuid4().hex}")
        now = utc_now()
        record.setdefault("trade_id", trade_id)
        record.setdefault("entry_time", now)
        record.setdefault("created_at", now)
        record.setdefault("updated_at", now)
        record.setdefault("status", "OPEN")
        record.setdefault("notes_json", {})
        with session_scope() as session:
            record = self._normalize_record_datetimes(record)
            record["notes_json"] = json.dumps(record.get("notes_json", {}), default=str)
            session.add(TradeHistory(**record))
        return trade_id

    def update_open_trade_history_metrics(self, symbol: str, current_price: float) -> int:
        updated = 0
        with session_scope() as session:
            row = session.execute(
                select(TradeHistory)
                .where(TradeHistory.symbol == symbol.upper(), TradeHistory.status == "OPEN")
                .order_by(TradeHistory.entry_time.desc())
            ).scalars().first()
            if row is None:
                return 0
            entry_price = float(row.entry_price or 0.0)
            if entry_price <= 0 or current_price <= 0:
                return 0
            pnl_pct = (float(current_price) / entry_price) - 1.0
            row.max_drawdown_during_trade = min(float(row.max_drawdown_during_trade or 0.0), pnl_pct)
            row.max_profit_during_trade = max(float(row.max_profit_during_trade or 0.0), pnl_pct)
            row.updated_at = utc_now()
            updated = 1
        return updated

    def close_trade_history(self, trade_id: str, updates: dict[str, object]) -> int:
        with session_scope() as session:
            row = session.execute(select(TradeHistory).where(TradeHistory.trade_id == trade_id)).scalars().first()
            if row is None:
                raise StorageError(f"TradeHistory not found for trade_id={trade_id}")
            self._apply_trade_history_close(row, updates)
        return 1

    def close_latest_open_trade(
        self,
        *,
        symbol: str,
        reason_closed: str,
        exit_price: float,
        fees_paid: float = 0.0,
        stop_loss_hit: bool = False,
        take_profit_hit: bool = False,
        trailing_stop_hit: bool = False,
        notes_json: dict[str, object] | None = None,
    ) -> dict[str, object] | None:
        with session_scope() as session:
            row = session.execute(
                select(TradeHistory)
                .where(TradeHistory.symbol == symbol.upper(), TradeHistory.status == "OPEN")
                .order_by(TradeHistory.entry_time.desc())
            ).scalars().first()
            if row is None:
                return None
            updates = {
                "exit_time": utc_now(),
                "exit_price": exit_price,
                "fees_paid": float(row.fees_paid or 0.0) + fees_paid,
                "reason_closed": reason_closed,
                "stop_loss_hit": stop_loss_hit,
                "take_profit_hit": take_profit_hit,
                "trailing_stop_hit": trailing_stop_hit,
                "notes_json": notes_json or {},
            }
            self._apply_trade_history_close(row, updates)
            payload = self._deserialize_trade_history(row)
        feedback = self._build_trade_feedback(payload)
        self.save_live_trade_feedback(feedback)
        return payload

    def get_trade_history(self, *, status: str | None = None, symbol: str | None = None, limit: int | None = None) -> pd.DataFrame:
        with SessionLocal() as session:
            query = select(TradeHistory).order_by(TradeHistory.entry_time.desc())
            if status:
                query = query.where(TradeHistory.status == status)
            if symbol:
                query = query.where(TradeHistory.symbol == symbol.upper())
            rows = session.execute(query).scalars().all()
        frame = pd.DataFrame([self._deserialize_trade_history(row) for row in rows])
        if limit is not None and not frame.empty:
            frame = frame.head(limit)
        return frame

    def save_audit_event(self, event: dict[str, object]) -> int:
        with session_scope() as session:
            payload = event.copy()
            payload["payload_json"] = json.dumps(payload.get("payload_json", {}), default=str)
            session.add(AuditEvent(**payload))
        return 1

    def get_audit_events(self, limit: int | None = None) -> pd.DataFrame:
        with SessionLocal() as session:
            rows = session.execute(select(AuditEvent).order_by(AuditEvent.timestamp.desc())).scalars().all()
        frame = pd.DataFrame([self._deserialize_json_field(row, "payload_json") for row in rows])
        if limit is not None and not frame.empty:
            frame = frame.head(limit)
        return frame

    def get_ranking_cycles(self, interval: str | None = None, limit: int | None = None) -> pd.DataFrame:
        with SessionLocal() as session:
            query = select(RankingCycle).order_by(RankingCycle.timestamp.desc())
            if interval:
                query = query.where(RankingCycle.interval == interval)
            rows = session.execute(query).scalars().all()
        frame = pd.DataFrame([self._deserialize_json_field(row, "payload_json") for row in rows])
        if limit is not None and not frame.empty:
            frame = frame.head(limit)
        return frame

    def get_latest_account_snapshot(self) -> dict[str, object] | None:
        with SessionLocal() as session:
            row = session.execute(select(AccountSnapshot).order_by(AccountSnapshot.timestamp.desc())).scalars().first()
        if row is None:
            return None
        payload = self._to_dict(row)
        payload["snapshot_json"] = json.loads(str(payload["snapshot_json"]))
        return payload

    def upsert_daily_performance(self, performance: dict[str, object]) -> int:
        target_date = performance["date"]
        if isinstance(target_date, datetime):
            target_date = target_date.date()
        with session_scope() as session:
            row = session.execute(select(DailyPerformance).where(DailyPerformance.date == target_date)).scalars().first()
            if row is None:
                session.add(DailyPerformance(**performance))
            else:
                for key, value in performance.items():
                    setattr(row, key, value)
        return 1

    def get_daily_performance(self, target_date: date | None = None) -> dict[str, object] | None:
        resolved_date = target_date or utc_now().date()
        with SessionLocal() as session:
            row = session.execute(select(DailyPerformance).where(DailyPerformance.date == resolved_date)).scalars().first()
        return None if row is None else self._to_dict(row)

    def list_daily_performance(self, limit: int | None = None) -> pd.DataFrame:
        with SessionLocal() as session:
            rows = session.execute(select(DailyPerformance).order_by(DailyPerformance.date.desc())).scalars().all()
        frame = pd.DataFrame([self._to_dict(row) for row in rows])
        if limit is not None and not frame.empty:
            frame = frame.head(limit)
        return frame

    def get_live_account_view(self) -> dict[str, object]:
        open_positions = self.get_open_positions()
        snapshot = self.get_latest_account_snapshot() or {}
        daily = self.get_daily_performance() or {}
        return {
            "account_snapshot": snapshot,
            "daily_performance": daily,
            "open_positions": open_positions.to_dict(orient="records"),
            "exposure_pct": snapshot.get("exposure_pct", 0.0),
            "open_positions_count": len(open_positions),
        }

    def cleanup_persisted_positions(self) -> dict[str, int]:
        with session_scope() as session:
            open_rows = session.execute(select(OpenPosition)).scalars().all()
            invalid_symbols: list[str] = []
            for row in open_rows:
                payload = self._to_dict(row)
                if self.is_valid_open_position(payload):
                    continue
                invalid_symbols.append(str(payload.get("symbol", "")).upper())
                session.delete(row)

            invalid_trades = session.execute(select(TradeExecution).where(TradeExecution.quantity <= 0)).scalars().all()
            removed_trade_rows = 0
            for row in invalid_trades:
                session.delete(row)
                removed_trade_rows += 1

        reconciled_trades = 0
        for symbol in invalid_symbols:
            reconciled_trades += self.reconcile_trade_execution(symbol=symbol, reason="invalid_position_removed")

        return {
            "invalid_open_positions_removed": len(invalid_symbols),
            "invalid_trade_rows_removed": removed_trade_rows,
            "orphan_open_trades_closed": reconciled_trades,
        }

    def reset_live_trading_state(self) -> dict[str, int]:
        now = utc_now()
        with session_scope() as session:
            open_positions_removed = len(session.execute(select(OpenPosition)).scalars().all())
            if open_positions_removed:
                session.execute(delete(OpenPosition))

            stuck_trades_removed = len(
                session.execute(select(TradeExecution).where(TradeExecution.status == "OPEN")).scalars().all()
            )
            if stuck_trades_removed:
                session.execute(delete(TradeExecution).where(TradeExecution.status == "OPEN"))

            latest_daily = session.execute(select(DailyPerformance).order_by(DailyPerformance.date.desc())).scalars().first()
            if latest_daily is not None:
                latest_daily.open_positions = 0
                latest_daily.consecutive_losses = 0
                latest_daily.paused = False
                latest_daily.updated_at = now

            latest_account = session.execute(select(AccountSnapshot).order_by(AccountSnapshot.timestamp.desc())).scalars().first()
            if latest_account is not None:
                snapshot_payload = json.loads(str(latest_account.snapshot_json))
                snapshot_payload["open_positions"] = []
                snapshot_payload["open_orders"] = []
                portfolio_payload = dict(snapshot_payload.get("portfolio", {}))
                portfolio_payload["open_positions"] = 0
                portfolio_payload["position_notional"] = 0.0
                portfolio_payload["exposure"] = 0.0
                portfolio_payload["unrealized_pnl"] = 0.0
                portfolio_payload["equity"] = float(latest_account.total_balance)
                portfolio_payload["cash"] = float(latest_account.total_balance)
                snapshot_payload["portfolio"] = portfolio_payload
                session.add(
                    AccountSnapshot(
                        timestamp=now,
                        mode=str(latest_account.mode),
                        total_balance=float(latest_account.total_balance),
                        free_balance=float(latest_account.total_balance),
                        locked_balance=0.0,
                        exposure_pct=0.0,
                        open_positions=0,
                        open_orders=0,
                        snapshot_json=json.dumps(snapshot_payload, default=str),
                    )
                )

        return {
            "open_positions_removed": open_positions_removed,
            "stuck_trades_removed": stuck_trades_removed,
        }

    @staticmethod
    def _deserialize_risk_event(model: RiskEvent) -> dict[str, object]:
        payload = StorageRepository._to_dict(model)
        payload["payload_json"] = json.loads(str(payload["payload_json"]))
        return payload

    @staticmethod
    def _deserialize_json_field(model: object, field_name: str) -> dict[str, object]:
        payload = StorageRepository._to_dict(model)
        payload[field_name] = json.loads(str(payload[field_name]))
        return payload

    def reconcile_trade_execution(
        self,
        *,
        symbol: str | None = None,
        order_id: str | None = None,
        reason: str,
    ) -> int:
        updated = 0
        with session_scope() as session:
            query = select(TradeExecution).where(TradeExecution.status == "OPEN")
            if order_id:
                query = query.where(TradeExecution.order_id == order_id)
            elif symbol:
                query = query.where(TradeExecution.symbol == str(symbol).upper())
            else:
                return 0
            rows = session.execute(query).scalars().all()
            for row in rows:
                row.status = "CLOSED"
                row.notes = reason
                updated += 1
        return updated

    def _apply_trade_history_close(self, row: TradeHistory, updates: dict[str, object]) -> None:
        exit_time = ensure_utc(updates.get("exit_time")) or utc_now()
        exit_price = self._as_float(updates.get("exit_price"))
        quantity = self._as_float(getattr(row, "quantity", 0.0))
        entry_price = self._as_float(getattr(row, "entry_price", 0.0))
        total_fees = self._as_float(updates.get("fees_paid", getattr(row, "fees_paid", 0.0)))
        pnl = ((exit_price - entry_price) * quantity) - total_fees
        pnl_percent = ((exit_price / entry_price) - 1.0) if entry_price > 0 and exit_price > 0 else 0.0
        try:
            duration_minutes = max(0.0, safe_utc_diff(exit_time, getattr(row, "entry_time", None)).total_seconds() / 60.0)
        except Exception as exc:
            self.logger.warning("trade_history_duration_utc_normalization_failed error=%s", exc)
            duration_minutes = 0.0
        for key, value in updates.items():
            if key == "notes_json":
                setattr(row, key, json.dumps(value or {}, default=str))
            else:
                setattr(row, key, self._normalize_temporal_value(key, value))
        row.exit_time = exit_time
        row.exit_price = exit_price
        row.fees_paid = total_fees
        row.pnl = pnl
        row.pnl_percent = pnl_percent
        row.holding_minutes = duration_minutes
        row.trade_duration_minutes = duration_minutes
        row.was_successful = pnl > 0
        row.prediction_correct = bool(row.ranking_score >= 0.5 and pnl > 0) or bool(row.ranking_score < 0.5 and pnl <= 0)
        row.status = "CLOSED"
        row.updated_at = utc_now()
        feedback = self._build_trade_feedback(self._deserialize_trade_history(row))
        row.decision_quality_score = self._as_float(feedback.get("quality_score", 5.0))
        row.decision_quality_label = str(feedback.get("quality_label", "neutral"))

    @staticmethod
    def _deserialize_trade_history(model: TradeHistory) -> dict[str, object]:
        payload = StorageRepository._to_dict(model)
        payload["notes_json"] = json.loads(str(payload.get("notes_json", "{}")))
        return payload

    @staticmethod
    def _deserialize_retraining_run(model: RetrainingRun) -> dict[str, object]:
        payload = StorageRepository._to_dict(model)
        payload["metrics_json"] = json.loads(str(payload.get("metrics_json", "{}")))
        payload["notes_json"] = json.loads(str(payload.get("notes_json", "{}")))
        return payload

    @staticmethod
    def _deserialize_model_version(model: ModelVersion) -> dict[str, object]:
        payload = StorageRepository._to_dict(model)
        payload["features_used"] = json.loads(str(payload.get("features_used", "[]")))
        payload["metrics_json"] = json.loads(str(payload.get("metrics_json", "{}")))
        payload["params_json"] = json.loads(str(payload.get("params_json", "{}")))
        return payload

    @classmethod
    def _build_trade_feedback(cls, trade_payload: Mapping[str, object]) -> dict[str, object]:
        pnl_percent = cls._as_float(trade_payload.get("pnl_percent"))
        max_profit = cls._as_float(trade_payload.get("max_profit_during_trade"))
        trailing_hit = bool(trade_payload.get("trailing_stop_hit"))
        stop_hit = bool(trade_payload.get("stop_loss_hit"))
        take_profit_hit = bool(trade_payload.get("take_profit_hit"))
        ranking_score = cls._as_float(trade_payload.get("ranking_score"))
        prediction_correct = bool(trade_payload.get("prediction_correct"))
        could_have_earned_more = max_profit > max(pnl_percent + 0.01, 0.02)
        stop_too_tight = stop_hit and max_profit > 0.01
        take_profit_too_low = take_profit_hit and could_have_earned_more
        quality_score = 5.0
        if pnl_percent >= 0.04 and prediction_correct:
            quality_score = 10.0
        elif pnl_percent > 0 and prediction_correct:
            quality_score = 7.0
        elif pnl_percent <= -0.03:
            quality_score = 1.0
        elif pnl_percent < 0:
            quality_score = 3.0
        quality_label = "neutral"
        if quality_score >= 9:
            quality_label = "excellent"
        elif quality_score >= 7:
            quality_label = "good_entry_bad_exit" if trailing_hit or take_profit_too_low else "good"
        elif quality_score <= 1:
            quality_label = "totally_incorrect"
        elif quality_score <= 3:
            quality_label = "bad"
        return {
            "trade_id": str(trade_payload.get("trade_id", "")),
            "symbol": str(trade_payload.get("symbol", "")),
            "timestamp": utc_now(),
            "quality_score": quality_score,
            "quality_label": quality_label,
            "prediction_correct": prediction_correct,
            "ranking_correct": ranking_score >= 0.5 and pnl_percent > 0,
            "timing_correct": pnl_percent > -0.01,
            "stop_too_tight": stop_too_tight,
            "take_profit_too_low": take_profit_too_low,
            "could_have_earned_more": could_have_earned_more,
            "feedback_json": {
                "pnl_percent": pnl_percent,
                "max_profit_during_trade": max_profit,
                "stop_loss_hit": stop_hit,
                "take_profit_hit": take_profit_hit,
                "trailing_stop_hit": trailing_hit,
            },
        }

    def _sanitize_open_positions_frame(self, frame: pd.DataFrame) -> pd.DataFrame:
        if frame.empty:
            return frame
        records = frame.to_dict(orient="records")
        valid_records = [record for record in records if self.is_valid_open_position(record)]
        invalid_symbols = [
            str(record.get("symbol", "")).upper()
            for record in records
            if not self.is_valid_open_position(record) and str(record.get("symbol", "")).strip()
        ]
        for symbol in invalid_symbols:
            self.close_open_position(symbol, reason="invalid_position_removed")
        if not valid_records:
            return pd.DataFrame(columns=frame.columns)
        return pd.DataFrame(valid_records).reset_index(drop=True)

    @classmethod
    def is_valid_open_position(cls, position: Mapping[str, object] | dict[str, object]) -> bool:
        symbol = str(position.get("symbol", "")).strip().upper()
        status = str(position.get("status", "open")).strip().lower()
        quantity = cls._as_float(position.get("quantity", 0.0))
        entry_price = cls._as_float(position.get("entry_price", 0.0))
        current_price = cls._as_float(position.get("current_price", 0.0))
        executed_qty = position.get("executed_qty")
        pnl = position.get("pnl")
        exit_price = position.get("exit_price")
        if not symbol:
            return False
        if quantity <= 0 or entry_price <= 0 or current_price <= 0:
            return False
        if status in cls.INVALID_POSITION_STATUSES:
            return False
        if executed_qty is not None and cls._as_float(executed_qty) <= 0:
            return False
        if pnl is not None and exit_price is not None and cls._as_float(exit_price) > 0:
            return False
        return True

    @staticmethod
    def _as_float(value: object) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _to_dict(model: object) -> dict[str, object]:
        if model is None:
            raise StorageError("Cannot serialize empty model")
        payload = {column.name: getattr(model, column.name) for column in model.__table__.columns}  # type: ignore[attr-defined]
        return StorageRepository._normalize_record_datetimes(payload)

    @classmethod
    def _normalize_record_datetimes(cls, record: Mapping[str, object] | dict[str, object]) -> dict[str, object]:
        normalized = dict(record)
        for key, value in list(normalized.items()):
            normalized[key] = cls._normalize_temporal_value(key, value)
        return normalized

    @classmethod
    def _normalize_temporal_value(cls, key: str, value: object) -> object:
        if value is None:
            return None
        if key == "date":
            normalized = ensure_utc(value)
            return normalized.date() if normalized is not None else value
        if key in cls.DATETIME_FIELDS:
            normalized = ensure_utc(value)
            return normalized if normalized is not None else value
        if isinstance(value, (datetime, pd.Timestamp)):
            normalized = ensure_utc(value)
            return normalized if normalized is not None else value
        return value

    @staticmethod
    def _normalize_ranking_record(record: dict[str, object]) -> dict[str, object]:
        allowed_columns = {
            "timestamp",
            "symbol",
            "score",
            "final_score",
            "rank",
            "heuristic_score",
            "ml_probability",
            "news_score",
            "market_sentiment_adjustment",
            "momentum_component",
            "volume_component",
            "trend_component",
            "rsi_component",
            "technical_score",
            "trend_score",
            "volatility_score",
            "volume_score",
            "risk_score",
            "regime_score",
            "market_regime",
        }
        normalized = {key: value for key, value in record.items() if key in allowed_columns}
        score_value = normalized.get("score")
        if pd.isna(score_value) and "final_score" in normalized:
            score_value = normalized.get("final_score")
        if pd.isna(score_value) and "heuristic_score" in normalized:
            score_value = normalized.get("heuristic_score")
        if pd.isna(score_value):
            raise StorageError(f"Ranking record for {record.get('symbol', '<unknown>')} is missing required score")
        normalized["score"] = float(score_value)
        normalized.pop("final_score", None)
        float_defaults = {
            "heuristic_score": 0.0,
            "ml_probability": 0.0,
            "news_score": 0.0,
            "market_sentiment_adjustment": 0.0,
            "momentum_component": 0.0,
            "volume_component": 0.0,
            "trend_component": 0.0,
            "rsi_component": 0.0,
            "technical_score": 0.0,
            "trend_score": 0.0,
            "volatility_score": 0.0,
            "volume_score": 0.0,
            "risk_score": 0.0,
            "regime_score": 0.0,
        }
        for key, default in float_defaults.items():
            value = normalized.get(key, default)
            normalized[key] = default if pd.isna(value) else float(value)
        normalized["market_regime"] = str(normalized.get("market_regime", "sideways"))
        if "rank" in normalized and pd.notna(normalized["rank"]):
            normalized["rank"] = int(normalized["rank"])
        return normalized
