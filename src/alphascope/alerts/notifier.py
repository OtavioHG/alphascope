from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from alphascope.alerts.alert_dispatcher import AlertDispatcher
from alphascope.alerts.templates import render_critical_error
from alphascope.alerts.telegram_notifier import TelegramNotifier


class AlertNotifier:
    def __init__(
        self,
        telegram: TelegramNotifier | None = None,
        alerts_dir: str | Path = "data/processed/alerts",
    ) -> None:
        alerts_path = Path(alerts_dir)
        alerts_path.mkdir(parents=True, exist_ok=True)
        self.dispatcher = AlertDispatcher(
            telegram=telegram,
            history_path=alerts_path / "alerts.jsonl",
            state_path=alerts_path / "alerts_state.json",
        )

    def send_alert(self, alert_type: str, title: str, payload: dict[str, Any]) -> dict[str, Any]:
        message = self._format_message(title, payload)
        return {
            "alert_type": alert_type,
            "title": title,
            "payload": payload,
            "message": message,
            "created_at": datetime.now(UTC).isoformat(),
            "record": self.dispatcher.dispatch_raw(alert_type, title, message, payload),
        }

    def strong_signal(self, payload: dict[str, Any], side: str) -> dict[str, Any]:
        return self.send_alert(f"strong_{side.lower()}_signal", f"ALPHASCOPE ALERT - STRONG {side}", payload)

    def trade_executed(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"record": self.dispatcher.trade_opened(payload)}

    def trade_closed(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"record": self.dispatcher.trade_closed(payload)}

    def drawdown_alert(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.send_alert("drawdown_alert", "ALPHASCOPE ALERT - DRAWDOWN", payload)

    def system_error(self, payload: dict[str, Any]) -> dict[str, Any]:
        error_payload = {"component": "system", **payload}
        return {
            "record": self.dispatcher.dispatch_raw(
                "system_error",
                "ALPHASCOPE ALERT - SYSTEM ERROR",
                render_critical_error(error_payload),
                error_payload,
            )
        }

    def _format_message(self, title: str, payload: dict[str, Any]) -> str:
        lines = [title, ""]
        for key, value in payload.items():
            lines.append(f"{key}: {value}")
        return "\n".join(lines)
