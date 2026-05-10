"""Scheduling and runtime management for multi-agent execution."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from alphascope.agents.cache import MultiAgentCacheService
from alphascope.agents.learning_engine import MultiAgentLearningEngine
from alphascope.agents.metrics import MultiAgentMetricsService
from alphascope.agents.orchestrator import MultiAgentOrchestrator
from alphascope.automation.heartbeat import HeartbeatConfig, HeartbeatService
from alphascope.automation.scheduler import AutomationScheduler
from alphascope.config.settings import settings
from alphascope.utils.time import utc_now


class MultiAgentRuntime:
    def __init__(self, orchestrator: MultiAgentOrchestrator | None = None, *, cache: MultiAgentCacheService | None = None) -> None:
        self.orchestrator = orchestrator or MultiAgentOrchestrator()
        self.cache = cache or MultiAgentCacheService()
        self.learning = MultiAgentLearningEngine(self.orchestrator.repository)
        self.metrics = MultiAgentMetricsService()
        self.status_path = settings.runtime_dir / "multi_agent_runtime_status.json"
        self.scheduler_path = settings.runtime_dir / "multi_agent_scheduler_status.json"
        self.heartbeat_path = settings.runtime_dir / "multi_agent_heartbeat.json"
        self.status_path.parent.mkdir(parents=True, exist_ok=True)
        self.heartbeat = HeartbeatService(
            HeartbeatConfig(interval_seconds=settings.heartbeat_interval_seconds, heartbeat_file=self.heartbeat_path),
            payload_provider=self._heartbeat_payload,
        )

    def run_cycle(self, *, symbol: str, timeframe: str, mode: str = "paper", send_telegram: bool = True) -> dict[str, Any]:
        result = self.orchestrator.run(symbol=symbol, timeframe=timeframe, mode=mode, send_telegram=send_telegram)
        payload = result.to_dict()
        adaptive_learning: dict[str, Any] = {}
        if settings.multi_agent_apply_dynamic_thresholds_on_runtime_cycle:
            try:
                thresholds = self.learning.continuous_learning.apply_dynamic_thresholds()
                if thresholds:
                    adaptive_learning["dynamic_thresholds"] = thresholds
            except Exception as exc:
                adaptive_learning["dynamic_thresholds_error"] = str(exc)
        if settings.multi_agent_train_on_runtime_cycle and settings.continuous_learning_enabled:
            try:
                training_result = self.learning.maybe_retrain(symbols=[symbol], interval=timeframe, cycle_count=1)
                adaptive_learning["training"] = training_result
            except Exception as exc:
                adaptive_learning["training_error"] = str(exc)
        if adaptive_learning:
            payload["adaptive_learning"] = adaptive_learning
        self.cache.cache_context(symbol, timeframe, {"symbol": symbol, "timeframe": timeframe, "mode": mode, "updated_at": utc_now().isoformat()})
        self.cache.cache_result(symbol, timeframe, payload)
        updated_at = utc_now().isoformat()
        per_symbol_entry = {
            "symbol": symbol,
            "timeframe": timeframe,
            "decision": result.supervisor.decision,
            "final_score": result.supervisor.final_score,
            "execution_action": result.execution.action,
            "updated_at": updated_at,
            "mode": mode,
        }
        self._write_status(
            {
                "last_symbol": symbol,
                "last_timeframe": timeframe,
                "last_decision": result.supervisor.decision,
                "last_score": result.supervisor.final_score,
                "updated_at": updated_at,
                "mode": mode,
                "adaptive_learning": adaptive_learning,
                "last_execution_action": result.execution.action,
                "symbols": {symbol.upper(): per_symbol_entry},
            }
        )
        self.metrics.record_decision(payload)
        return payload

    def schedule_live(self, *, symbols: list[str], timeframe: str, cycle_seconds: int, duration_seconds: int | None = None) -> list[dict[str, Any]]:
        scheduler = AutomationScheduler(state_path=self.scheduler_path)
        self.heartbeat.start()
        try:
            for symbol in symbols:
                scheduler.register_job(
                    name=f"multi_agent_live_{symbol.lower()}",
                    func=lambda symbol=symbol: self.run_cycle(symbol=symbol.upper(), timeframe=timeframe, mode="live", send_telegram=True),
                    interval_seconds=cycle_seconds,
                    tags=("multi_agent", "live"),
                    max_retries=1,
                    retry_backoff_seconds=settings.retry_backoff_seconds,
                )
            scheduler.run_continuous(duration_seconds=duration_seconds, sleep_seconds=1)
            return scheduler.list_jobs()
        finally:
            self.heartbeat.stop()

    def train_models(self, *, symbols: list[str], timeframe: str, cycle_count: int = 1) -> dict[str, Any]:
        result = self.learning.maybe_retrain(symbols=symbols, interval=timeframe, cycle_count=cycle_count)
        self._write_status({"last_training": result, "updated_at": utc_now().isoformat()})
        return result

    def status(self) -> dict[str, Any]:
        payload = {}
        if self.status_path.exists():
            payload = json.loads(self.status_path.read_text(encoding="utf-8"))
        payload["cache"] = self.cache.read_status()
        payload["heartbeat"] = json.loads(self.heartbeat_path.read_text(encoding="utf-8")) if self.heartbeat_path.exists() else {}
        payload["scheduler"] = json.loads(self.scheduler_path.read_text(encoding="utf-8")) if self.scheduler_path.exists() else {}
        self.metrics.record_runtime_status(payload)
        return payload

    def close(self) -> None:
        self.orchestrator.close()
        self.heartbeat.stop()

    def _write_status(self, payload: dict[str, Any]) -> None:
        current = {}
        if self.status_path.exists():
            current = json.loads(self.status_path.read_text(encoding="utf-8"))
        if isinstance(current.get("symbols"), dict) and isinstance(payload.get("symbols"), dict):
            merged_symbols = dict(current["symbols"])
            merged_symbols.update(payload["symbols"])
            payload = payload.copy()
            payload["symbols"] = merged_symbols
        current.update(payload)
        self.status_path.write_text(json.dumps(current, indent=2, ensure_ascii=False), encoding="utf-8")

    def _heartbeat_payload(self) -> dict[str, Any]:
        cache_status = self.cache.read_status()
        return {
            "component": "multi_agent",
            "backend": cache_status.get("backend"),
            "last_runtime_status": json.loads(self.status_path.read_text(encoding="utf-8")) if self.status_path.exists() else {},
        }
