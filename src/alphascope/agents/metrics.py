"""Prometheus-friendly metrics for the multi-agent runtime."""

from __future__ import annotations

from typing import Any

from alphascope.monitoring.metrics import MetricsCollector


class MultiAgentMetricsService:
    def __init__(self, collector: MetricsCollector | None = None) -> None:
        self.collector = collector or MetricsCollector()

    def record_decision(self, payload: dict[str, Any]) -> None:
        symbol = str(payload.get("symbol", "UNKNOWN"))
        timeframe = str(payload.get("timeframe", "1h"))
        supervisor = payload.get("supervisor", {}) if isinstance(payload.get("supervisor"), dict) else {}
        execution = payload.get("execution", {}) if isinstance(payload.get("execution"), dict) else {}
        market_output = payload.get("market_output", {}) if isinstance(payload.get("market_output"), dict) else {}
        news_output = payload.get("news_output", {}) if isinstance(payload.get("news_output"), dict) else {}
        risk_output = payload.get("risk_output", {}) if isinstance(payload.get("risk_output"), dict) else {}
        memory_output = payload.get("memory_output", {}) if isinstance(payload.get("memory_output"), dict) else {}

        self.collector.emit("multi_agent_final_score", float(supervisor.get("final_score", 0.0) or 0.0), {"symbol": symbol, "timeframe": timeframe, "decision": str(supervisor.get("decision", "HOLD"))})
        self.collector.emit("multi_agent_execution_action", 1.0, {"symbol": symbol, "timeframe": timeframe, "action": str(execution.get("action", "unknown"))})
        for agent_name, output in {
            "market_intelligence": market_output,
            "news_sentiment": news_output,
            "risk_manager": risk_output,
            "memory_engine": memory_output,
        }.items():
            self.collector.emit("multi_agent_agent_confidence", float(output.get("confidence", 0.0) or 0.0), {"symbol": symbol, "timeframe": timeframe, "agent": agent_name, "signal": str(output.get("signal", "hold"))})
            self.collector.emit("multi_agent_agent_score", float(output.get("score", 0.0) or 0.0), {"symbol": symbol, "timeframe": timeframe, "agent": agent_name})

    def record_runtime_status(self, payload: dict[str, Any]) -> None:
        cache = payload.get("cache", {}) if isinstance(payload.get("cache"), dict) else {}
        heartbeat = payload.get("heartbeat", {}) if isinstance(payload.get("heartbeat"), dict) else {}
        scheduler = payload.get("scheduler", {}) if isinstance(payload.get("scheduler"), dict) else {}
        self.collector.emit("multi_agent_scheduler_jobs", float(scheduler.get("job_count", 0) or 0), {"backend": str(cache.get("backend", "unknown"))})
        self.collector.emit("multi_agent_heartbeat_up", 1.0 if heartbeat else 0.0, {"backend": str(cache.get("backend", "unknown"))})
