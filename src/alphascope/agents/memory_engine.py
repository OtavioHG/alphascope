"""Historical memory and offline intelligence for multi-agent trading."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pandas as pd

from alphascope.agents.schemas import AgentOutput, MultiAgentContext
from alphascope.agents.scoring_engine import ScoringEngine
from alphascope.config.settings import settings

logger = logging.getLogger(__name__)


class MemoryEngine:
    def __init__(self, repository) -> None:
        self.repository = repository

    def analyze(self, context: MultiAgentContext) -> AgentOutput:
        history = self.repository.get_recent_consensus(symbol=context.symbol, limit=30)
        features = context.features or {}
        ranking = context.ranking or {}
        wins = sum(1 for row in history if float(row.get("realized_pnl", 0.0) or 0.0) > 0)
        losses = sum(1 for row in history if float(row.get("realized_pnl", 0.0) or 0.0) < 0)
        hit_rate = wins / max(1, wins + losses)
        relative_volume = float(features.get("relative_volume", 1.0) or 1.0)
        ranking_score = float(ranking.get("score", 0.5) or 0.5)
        combined = max(0.0, min(1.0, 0.45 + (hit_rate - 0.5) * 0.35 + (ranking_score - 0.5) * 0.25 + (relative_volume - 1.0) * 0.10))
        if combined >= 0.67:
            signal = "buy"
        elif combined <= 0.33:
            signal = "sell"
        else:
            signal = "hold"
        confidence = max(0.30, min(0.85, 0.40 + abs(combined - 0.5) * 1.4))
        reasoning = (
            f"Memória local com hit rate {hit_rate:.2%}, {wins} ganhos, {losses} perdas e score histórico ajustado"
            if history
            else "Sem histórico suficiente; usando heurística local de fallback"
        )
        model_config = settings.multi_agent_model_registry["memory"]
        return AgentOutput(
            agent="memory_engine",
            signal=signal,
            confidence=confidence,
            score=ScoringEngine.signal_score(signal, confidence),
            reasoning=reasoning,
            metadata={
                "historical_hit_rate": round(hit_rate, 4),
                "winning_patterns": wins,
                "losing_patterns": losses,
                "ranking_score": round(ranking_score, 4),
                "inference_backend": "local_memory_proxy",
                "external_llm_available": settings.external_llm_available,
                "configured_primary_model": model_config["primary"],
                "configured_fallback_model": model_config["fallback"],
            },
            model_name=str(model_config["active"] if history and model_config["external"] else model_config["fallback"]),
            fallback_used=not (bool(history) and bool(model_config["external"])),
        )

    def persist_context_memory(self, result: dict[str, Any]) -> None:
        symbol = str(result["symbol"])
        timeframe = str(result["timeframe"])
        created_at = result["supervisor"]["created_at"]
        self.repository.save_memory_entry(
            table_name="agent_memory",
            payload={
                "symbol": symbol,
                "timeframe": timeframe,
                "memory_type": "agent_run",
                "summary": f"{symbol} {timeframe} -> {result['supervisor']['decision']} ({result['supervisor']['final_score']:.4f})",
                "payload_json": result,
                "created_at": created_at,
            },
        )
        self.repository.save_memory_entry(
            table_name="market_context_memory",
            payload={
                "symbol": symbol,
                "timeframe": timeframe,
                "memory_type": "market_context",
                "summary": result["market_output"]["reasoning"],
                "payload_json": result["market_output"],
                "created_at": created_at,
            },
        )
        self.repository.save_memory_entry(
            table_name="news_memory",
            payload={
                "symbol": symbol,
                "timeframe": timeframe,
                "memory_type": "news_context",
                "summary": result["news_output"]["reasoning"],
                "payload_json": result["news_output"],
                "created_at": created_at,
            },
        )
        self.repository.save_memory_entry(
            table_name="risk_memory",
            payload={
                "symbol": symbol,
                "timeframe": timeframe,
                "memory_type": "risk_context",
                "summary": result["risk_output"]["reasoning"],
                "payload_json": result["risk_output"],
                "created_at": created_at,
            },
        )
        self.repository.save_memory_entry(
            table_name="strategy_memory",
            payload={
                "symbol": symbol,
                "timeframe": timeframe,
                "memory_type": "consensus_strategy",
                "summary": result["supervisor"]["reasoning"],
                "payload_json": result["supervisor"],
                "created_at": created_at,
            },
        )

    def export_training_datasets(self) -> list[str]:
        exports = {
            settings.training_data_dir / "agent_outputs.parquet": pd.DataFrame(self.repository.get_recent_agent_decisions(limit=500)),
            settings.training_data_dir / "trade_outcomes.parquet": pd.DataFrame(self.repository.get_recent_consensus(limit=500)),
            settings.training_data_dir / "news_patterns.parquet": pd.DataFrame(self.repository.get_memory_entries("news_memory", limit=500)),
            settings.training_data_dir / "risk_patterns.parquet": pd.DataFrame(self.repository.get_memory_entries("risk_memory", limit=500)),
        }
        written: list[str] = []
        Path(settings.training_data_dir).mkdir(parents=True, exist_ok=True)
        for path, frame in exports.items():
            if frame.empty:
                continue
            try:
                frame.to_parquet(path, index=False)
                written.append(str(path))
            except Exception as exc:
                fallback = path.with_suffix(".csv")
                frame.to_csv(fallback, index=False)
                written.append(str(fallback))
                logger.warning("Parquet export failed for %s: %s", path, exc)
        return written
