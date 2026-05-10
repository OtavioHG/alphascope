"""Audit helpers for multi-agent runs."""

from __future__ import annotations

from typing import Any


class AuditEngine:
    def __init__(self, repository) -> None:
        self.repository = repository

    def persist_full_audit(self, payload: dict[str, Any]) -> None:
        self.repository.save_trade_audit(
            {
                "symbol": payload["symbol"],
                "timeframe": payload["timeframe"],
                "decision": payload["supervisor"]["decision"],
                "final_score": payload["supervisor"]["final_score"],
                "summary": payload["supervisor"]["reasoning"],
                "payload_json": payload,
                "created_at": payload["supervisor"]["created_at"],
            }
        )
        self.repository.storage.save_audit_event(
            {
                "timestamp": payload["supervisor"]["created_at"],
                "action": "multi_agent_decision",
                "actor": "supervisor_agent",
                "source": "multi_agent",
                "target": payload["symbol"],
                "payload_json": {
                    "symbol": payload["symbol"],
                    "timeframe": payload["timeframe"],
                    "decision": payload["supervisor"]["decision"],
                    "final_score": payload["supervisor"]["final_score"],
                    "consensus": payload["supervisor"]["consensus"],
                    "reasoning": payload["supervisor"]["reasoning"],
                    "execution_action": payload["execution"]["action"],
                },
            }
        )
        self.repository.save_runtime_event(
            {
                "event_type": "multi_agent_cycle",
                "status": "completed",
                "symbol": payload["symbol"],
                "timeframe": payload["timeframe"],
                "summary": payload["execution"]["reasoning"],
                "payload_json": payload,
                "created_at": payload["supervisor"]["created_at"],
            }
        )
