"""Operational alert dispatcher with stateful deduplication."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from alphascope.alerts.alert_rules import AlertRuleEngine
from alphascope.alerts.telegram_notifier import TelegramNotifier, TelegramSendResult
from alphascope.config.settings import settings
from alphascope.core.logger import get_logger
from . import templates

logger = get_logger(__name__)


@dataclass(slots=True)
class AlertRecord:
    alert_type: str
    title: str
    message: str
    payload: dict[str, Any]
    created_at: str
    delivered: bool
    status_code: int | None = None
    error: str | None = None


class AlertDispatcher:
    """Evaluate and dispatch operational alerts to Telegram and local history."""

    def __init__(
        self,
        *,
        telegram: TelegramNotifier | None = None,
        rules: AlertRuleEngine | None = None,
        history_path: Path | None = None,
        state_path: Path | None = None,
    ) -> None:
        self.telegram = telegram or TelegramNotifier(
            settings.telegram_bot_token,
            settings.telegram_chat_id,
            enabled=settings.telegram_enabled or settings.enable_telegram_alerts,
            parse_mode=settings.telegram_parse_mode,
            timeout=settings.request_timeout,
            retries=settings.request_retries,
        )
        self.rules = rules or AlertRuleEngine()
        self.history_path = history_path or settings.alerts_history_file
        self.state_path = state_path or settings.alerts_state_file
        self.history_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.parent.mkdir(parents=True, exist_ok=True)

    def send_test_alert(self, *, source: str = "manual") -> AlertRecord:
        payload = {
            "app_name": settings.app_name,
            "environment": settings.environment,
            "source": source,
        }
        return self.dispatch_raw(
            "test_alert",
            "AlphaScope test alert",
            templates.render_test_alert(**payload),
            payload,
        )

    def pipeline_completed(self, payload: dict[str, Any]) -> AlertRecord:
        return self.dispatch_raw(
            "pipeline_completed",
            "Pipeline completed",
            templates.render_pipeline_completed(payload),
            payload,
        )

    def critical_error(self, *, component: str, error: str, context: dict[str, Any] | None = None) -> AlertRecord:
        payload = {"component": component, "error": error, **(context or {})}
        return self.dispatch_raw(
            "critical_error",
            "Critical error",
            templates.render_critical_error(payload),
            payload,
        )

    def top_ranking_changed(self, ranking: pd.DataFrame, *, min_score_delta: float = 0.0) -> AlertRecord | None:
        state = self._load_state()
        decision = self.rules.new_top_ranking(
            ranking,
            previous_symbol=state.get("last_top_symbol"),
            previous_score=state.get("last_top_score"),
            min_score_delta=min_score_delta,
        )
        if not decision.triggered:
            return None
        self._update_state(
            last_top_symbol=decision.payload.get("symbol"),
            last_top_score=decision.payload.get("score"),
        )
        return self.dispatch_raw(
            "new_top_ranking",
            "New top ranking",
            templates.render_top_ranking(decision.payload),
            decision.payload,
        )

    def trade_opened(self, payload: dict[str, Any]) -> AlertRecord:
        mode = str(payload.get("mode", "paper")).upper()
        return self.dispatch_raw(
            "trade_opened",
            f"Trade opened [{mode}]",
            templates.render_trade_opened(payload),
            payload,
        )

    def trade_closed(self, payload: dict[str, Any]) -> AlertRecord:
        mode = str(payload.get("mode", "paper")).upper()
        return self.dispatch_raw(
            "trade_closed",
            f"Trade closed [{mode}]",
            templates.render_trade_closed(payload),
            payload,
        )

    def portfolio_snapshot(self, snapshot: dict[str, Any], *, label: str = "Portfolio snapshot") -> AlertRecord:
        positions = snapshot.get("positions_json", {})
        payload = {
            "label": label,
            "timestamp": snapshot.get("timestamp"),
            "equity": snapshot.get("equity", 0.0),
            "cash": snapshot.get("cash", 0.0),
            "realized_pnl": snapshot.get("realized_pnl", 0.0),
            "unrealized_pnl": snapshot.get("unrealized_pnl", 0.0),
            "open_positions": len(positions) if isinstance(positions, dict) else 0,
        }
        return self.dispatch_raw(
            "portfolio_snapshot",
            label,
            templates.render_portfolio_snapshot(payload),
            payload,
        )

    def daemon_stopped(self, payload: dict[str, Any]) -> AlertRecord:
        self._update_state(last_daemon_status=payload.get("status"))
        return self.dispatch_raw(
            "daemon_stopped",
            "Daemon stopped",
            templates.render_daemon_stopped(payload),
            payload,
        )

    def runtime_summary(self, runtime_status: dict[str, Any], *, label: str = "Runtime summary") -> AlertRecord:
        payload = self._runtime_summary_payload(runtime_status, label=label)
        return self.dispatch_raw(
            "runtime_summary",
            label,
            templates.render_runtime_summary(payload),
            payload,
        )

    def multi_agent_decision(self, payload: dict[str, Any]) -> AlertRecord:
        return self.dispatch_raw(
            "multi_agent_decision",
            "Multi-Agent Decision",
            templates.render_multi_agent_decision(payload),
            payload,
        )

    def evaluate_runtime_alerts(self, runtime_status: dict[str, Any]) -> list[AlertRecord]:
        records: list[AlertRecord] = []
        state = self._load_state()

        heartbeat_decision = self.rules.heartbeat_lost(
            runtime_status,
            already_alerted=bool(state.get("heartbeat_alert_active")),
        )
        if heartbeat_decision.triggered:
            records.append(
                self.dispatch_raw(
                    "heartbeat_lost",
                    "Heartbeat alert",
                    templates.render_heartbeat_lost(heartbeat_decision.payload),
                    heartbeat_decision.payload,
                )
            )
            self._update_state(heartbeat_alert_active=True)
        elif state.get("heartbeat_alert_active"):
            recovery = runtime_status.get("recovery", {})
            if recovery.get("healthy", True):
                self._update_state(heartbeat_alert_active=False)

        daemon_decision = self.rules.daemon_stopped(
            runtime_status,
            previous_status=state.get("last_daemon_status"),
        )
        current_status = runtime_status.get("daemon", {}).get("status")
        self._update_state(last_daemon_status=current_status)
        if daemon_decision.triggered:
            records.append(
                self.dispatch_raw(
                    "daemon_stopped",
                    "Daemon stopped",
                    templates.render_daemon_stopped(daemon_decision.payload),
                    daemon_decision.payload,
                )
            )

        return records

    def dispatch_raw(self, alert_type: str, title: str, message: str, payload: dict[str, Any]) -> AlertRecord:
        telegram_result: TelegramSendResult = self.telegram.send_message(message)
        record = AlertRecord(
            alert_type=alert_type,
            title=title,
            message=message,
            payload=payload,
            created_at=datetime.now(UTC).isoformat(),
            delivered=telegram_result.delivered,
            status_code=telegram_result.status_code,
            error=telegram_result.error,
        )
        self._append_history(record)
        if not record.delivered and record.error:
            logger.warning("Alert %s was not delivered: %s", alert_type, record.error)
        return record

    def _append_history(self, record: AlertRecord) -> None:
        with self.history_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(record), ensure_ascii=False, default=str) + "\n")

    def _runtime_summary_payload(self, runtime_status: dict[str, Any], *, label: str) -> dict[str, Any]:
        latest_ranking = runtime_status.get("latest_ranking", {})
        latest_snapshot = runtime_status.get("latest_snapshot", {})
        return {
            "label": label,
            "daemon_status": runtime_status.get("daemon", {}).get("status"),
            "heartbeat_status": runtime_status.get("heartbeat", {}).get("status"),
            "top_symbol": latest_ranking.get("top_symbol"),
            "equity": latest_snapshot.get("equity", 0.0) or 0.0,
            "cash": latest_snapshot.get("cash", 0.0) or 0.0,
            "job_count": runtime_status.get("jobs", {}).get("job_count", 0),
            "issue_count": len(runtime_status.get("recovery", {}).get("issues", [])),
            "multi_agent_decision": runtime_status.get("multi_agent", {}).get("last_decision"),
            "multi_agent_score": runtime_status.get("multi_agent", {}).get("last_score"),
        }

    def _load_state(self) -> dict[str, Any]:
        if not self.state_path.exists():
            return {}
        return json.loads(self.state_path.read_text(encoding="utf-8"))

    def _update_state(self, **updates: Any) -> None:
        state = self._load_state()
        state.update(updates)
        self.state_path.write_text(json.dumps(state, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
