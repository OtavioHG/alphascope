"""Persistence facade for multi-agent workflows."""

from __future__ import annotations

import json
from collections import Counter
from typing import Any

from sqlalchemy import select

import alphascope.agents.models as models
from alphascope.storage.database import SessionLocal, session_scope
from alphascope.storage.repositories import StorageRepository
from alphascope.utils.time import ensure_utc, utc_now


class MultiAgentRepository:
    MEMORY_TABLES = {
        "agent_memory": models.MemoryRecord,
        "historical_patterns": models.HistoricalPatternRecord,
        "winning_trade_patterns": models.WinningTradePatternRecord,
        "losing_trade_patterns": models.LosingTradePatternRecord,
        "market_context_memory": models.MarketContextMemoryRecord,
        "news_memory": models.NewsMemoryRecord,
        "risk_memory": models.RiskMemoryRecord,
        "strategy_memory": models.StrategyMemoryRecord,
    }

    def __init__(self, storage: StorageRepository | None = None) -> None:
        self.storage = storage or StorageRepository()

    def build_context(self, *, symbol: str, timeframe: str, limit: int = 120) -> dict[str, Any]:
        candles = self.storage.get_candles(symbol=symbol, interval=timeframe, limit=limit).to_dict(orient="records")
        features_frame = self.storage.get_features(symbol=symbol, interval=timeframe)
        ranking_frame = self.storage.get_latest_ranking(interval=timeframe)
        market_snapshots = self.storage.get_market_snapshots(symbol=symbol, timeframe=timeframe, limit=10).to_dict(orient="records")
        feature_snapshots = self.storage.get_feature_snapshots(symbol=symbol, timeframe=timeframe, limit=10).to_dict(orient="records")
        predictions = self.storage.get_model_predictions(symbol=symbol, timeframe=timeframe, limit=10).to_dict(orient="records")
        latest_account = self.storage.get_latest_account_snapshot() or {}
        open_positions = self.storage.get_open_positions().to_dict(orient="records")
        daily = self.storage.get_daily_performance() or {}
        latest_feature = features_frame.iloc[-1].to_dict() if not features_frame.empty else {}
        ranking_row = {}
        if not ranking_frame.empty and "symbol" in ranking_frame.columns:
            matches = ranking_frame.loc[ranking_frame["symbol"] == symbol.upper()]
            if matches.empty:
                matches = ranking_frame.head(1)
            ranking_row = matches.iloc[0].to_dict() if not matches.empty else {}
        return {
            "symbol": symbol.upper(),
            "timeframe": timeframe,
            "candles": candles,
            "features": latest_feature,
            "ranking": ranking_row,
            "account": latest_account,
            "open_positions": open_positions,
            "daily_performance": daily,
            "market_snapshots": market_snapshots,
            "feature_snapshots": feature_snapshots,
            "model_predictions": predictions,
            "recent_consensus": self.get_recent_consensus(symbol=symbol, limit=10),
            "recent_agent_decisions": self.get_recent_agent_decisions(symbol=symbol, limit=20),
        }

    def save_agent_output(self, *, symbol: str, timeframe: str, output: dict[str, Any]) -> None:
        created_at = ensure_utc(output.get("created_at")) or utc_now()
        with session_scope() as session:
            session.add(
                models.AgentDecisionRecord(
                    created_at=created_at,
                    symbol=symbol,
                    timeframe=timeframe,
                    agent_name=str(output.get("agent")),
                    signal=str(output.get("signal")),
                    confidence=float(output.get("confidence", 0.0) or 0.0),
                    score=float(output.get("score", 0.0) or 0.0),
                    model_name=str(output.get("model_name", "local")),
                    reasoning=str(output.get("reasoning", "")),
                    payload_json=json.dumps(output, default=str),
                )
            )
            session.add(
                models.ModelOutputRecord(
                    created_at=created_at,
                    symbol=symbol,
                    timeframe=timeframe,
                    provider="multi_agent",
                    model_name=str(output.get("model_name", "local")),
                    output_type=str(output.get("agent", "agent")),
                    payload_json=json.dumps(output, default=str),
                )
            )

    def save_debate_messages(self, *, symbol: str, timeframe: str, debate: list[dict[str, Any]]) -> None:
        with session_scope() as session:
            for item in debate:
                session.add(
                    models.AgentDebateRecord(
                        created_at=ensure_utc(item.get("created_at")) or utc_now(),
                        symbol=symbol,
                        timeframe=timeframe,
                        round_id=int(item.get("round_id", 1) or 1),
                        speaker=str(item.get("speaker")),
                        stance=str(item.get("stance")),
                        target_agent=item.get("target_agent"),
                        message=str(item.get("message", "")),
                        payload_json=json.dumps(item, default=str),
                    )
                )

    def save_consensus(self, payload: dict[str, Any], *, symbol: str, timeframe: str) -> None:
        created_at = ensure_utc(payload.get("created_at")) or utc_now()
        with session_scope() as session:
            session.add(
                models.TradeConsensusRecord(
                    created_at=created_at,
                    symbol=symbol,
                    timeframe=timeframe,
                    decision=str(payload.get("decision")),
                    final_score=float(payload.get("final_score", 0.0) or 0.0),
                    consensus=str(payload.get("consensus", "")),
                    reasoning=str(payload.get("reasoning", "")),
                    realized_pnl=float(payload.get("realized_pnl", 0.0) or 0.0),
                    payload_json=json.dumps(payload, default=str),
                )
            )

    def save_trade_audit(self, payload: dict[str, Any]) -> None:
        with session_scope() as session:
            session.add(
                models.TradeAuditRecord(
                    created_at=ensure_utc(payload.get("created_at")) or utc_now(),
                    symbol=str(payload.get("symbol")),
                    timeframe=str(payload.get("timeframe")),
                    decision=str(payload.get("decision")),
                    final_score=float(payload.get("final_score", 0.0) or 0.0),
                    summary=str(payload.get("summary", "")),
                    payload_json=json.dumps(payload.get("payload_json", {}), default=str),
                )
            )

    def save_runtime_event(self, payload: dict[str, Any]) -> dict[str, Any]:
        record = payload.copy()
        with session_scope() as session:
            session.add(
                models.RuntimeEventRecord(
                    created_at=ensure_utc(record.get("created_at")) or utc_now(),
                    event_type=str(record.get("event_type", "multi_agent_cycle")),
                    status=str(record.get("status", "completed")),
                    symbol=record.get("symbol"),
                    timeframe=record.get("timeframe"),
                    summary=str(record.get("summary", "")),
                    payload_json=json.dumps(record.get("payload_json", record), default=str),
                )
            )
        return record

    def save_memory_entry(self, *, table_name: str, payload: dict[str, Any]) -> None:
        model = self.MEMORY_TABLES[table_name]
        with session_scope() as session:
            kwargs = payload.copy()
            kwargs["created_at"] = ensure_utc(kwargs.get("created_at")) or utc_now()
            kwargs["payload_json"] = json.dumps(kwargs.get("payload_json", {}), default=str)
            session.add(model(**kwargs))

    def get_memory_entries(self, table_name: str, *, limit: int = 100) -> list[dict[str, Any]]:
        model = self.MEMORY_TABLES[table_name]
        with SessionLocal() as session:
            rows = session.execute(select(model).order_by(model.created_at.desc())).scalars().all()
        return [self._deserialize(row, "payload_json") for row in rows[:limit]]

    def get_recent_agent_decisions(self, *, symbol: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        with SessionLocal() as session:
            query = select(models.AgentDecisionRecord).order_by(models.AgentDecisionRecord.created_at.desc())
            if symbol:
                query = query.where(models.AgentDecisionRecord.symbol == symbol.upper())
            rows = session.execute(query).scalars().all()
        return [self._deserialize(row, "payload_json") for row in rows[:limit]]

    def get_recent_debates(self, *, symbol: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        with SessionLocal() as session:
            query = select(models.AgentDebateRecord).order_by(models.AgentDebateRecord.created_at.desc())
            if symbol:
                query = query.where(models.AgentDebateRecord.symbol == symbol.upper())
            rows = session.execute(query).scalars().all()
        return [self._deserialize(row, "payload_json") for row in rows[:limit]]

    def get_recent_consensus(self, *, symbol: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        with SessionLocal() as session:
            query = select(models.TradeConsensusRecord).order_by(models.TradeConsensusRecord.created_at.desc())
            if symbol:
                query = query.where(models.TradeConsensusRecord.symbol == symbol.upper())
            rows = session.execute(query).scalars().all()
        return [self._deserialize(row, "payload_json") for row in rows[:limit]]

    def compare_agent_decisions(self, *, symbol: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        decisions = self.get_recent_agent_decisions(symbol=symbol, limit=limit)
        grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
        for row in decisions:
            key = (str(row.get("symbol", "?")), str(row.get("created_at", "?"))[:19])
            grouped.setdefault(key, []).append(row)
        comparison: list[dict[str, Any]] = []
        for (row_symbol, created_at), rows in grouped.items():
            signals = Counter(str(row.get("signal", "hold")) for row in rows)
            comparison.append(
                {
                    "symbol": row_symbol,
                    "created_at": created_at,
                    "signals": dict(signals),
                    "agents": {str(row.get("agent")): str(row.get("signal")) for row in rows},
                }
            )
        return comparison[:limit]

    def get_agent_performance(self, *, limit: int = 200) -> list[dict[str, Any]]:
        decisions = self.get_recent_agent_decisions(limit=limit)
        grouped: dict[str, list[dict[str, Any]]] = {}
        for row in decisions:
            grouped.setdefault(str(row.get("agent")), []).append(row)
        performance: list[dict[str, Any]] = []
        for agent, rows in grouped.items():
            avg_confidence = sum(float(row.get("confidence", 0.0) or 0.0) for row in rows) / max(1, len(rows))
            buy_rate = sum(1 for row in rows if row.get("signal") == "buy") / max(1, len(rows))
            hold_rate = sum(1 for row in rows if row.get("signal") == "hold") / max(1, len(rows))
            performance.append(
                {
                    "agent": agent,
                    "decisions": len(rows),
                    "avg_confidence": round(avg_confidence, 4),
                    "buy_rate": round(buy_rate, 4),
                    "hold_rate": round(hold_rate, 4),
                }
            )
        performance.sort(key=lambda item: (-item["avg_confidence"], -item["decisions"]))
        return performance

    def get_dynamic_weight_multipliers(self) -> dict[str, float]:
        performance = self.get_agent_performance(limit=300)
        mapping = {
            "market_intelligence": "nemotron",
            "risk_manager": "nemotron",
            "news_sentiment": "gpt_oss",
            "memory_engine": "trinity",
        }
        multipliers = {"nemotron": 1.0, "gpt_oss": 1.0, "minimax": 1.0, "trinity": 1.0}
        for row in performance:
            bucket = mapping.get(str(row.get("agent")))
            if bucket is None:
                continue
            multipliers[bucket] += (float(row.get("avg_confidence", 0.0) or 0.0) - 0.5) * 0.5
        return multipliers

    def open_execution_intent(self, *, symbol: str, timeframe: str, execution: dict[str, Any], consensus: dict[str, Any]) -> None:
        if execution.get("action") != "place_order":
            return
        now = utc_now()
        order_id = f"multiagent-{symbol.lower()}-{int(now.timestamp())}"
        self.storage.save_trade_execution(
            {
                "timestamp": now,
                "symbol": symbol,
                "side": execution.get("side", "BUY"),
                "quantity": max(0.0, float(execution.get("size_usd", 0.0) or 0.0)),
                "entry_price": 0.0,
                "exit_price": None,
                "stop_loss_price": float(execution.get("stop_loss", 0.0) or 0.0),
                "take_profit_price": float(execution.get("take_profit", 0.0) or 0.0),
                "pnl": 0.0,
                "pnl_pct": 0.0,
                "status": "APPROVED",
                "order_id": order_id,
                "source": "multi_agent",
                "mode": "paper",
                "confidence_score": float(consensus.get("final_score", 0.0) or 0.0),
                "notes": execution.get("reasoning"),
                "created_at": now,
            }
        )

    @staticmethod
    def _deserialize(row: Any, field_name: str) -> dict[str, Any]:
        payload = {column.name: getattr(row, column.name) for column in row.__table__.columns}
        raw = payload.get(field_name)
        try:
            parsed = json.loads(raw) if isinstance(raw, str) else raw
        except Exception:
            parsed = raw
        if isinstance(parsed, dict):
            payload.update(parsed)
        payload[field_name] = parsed
        return payload
