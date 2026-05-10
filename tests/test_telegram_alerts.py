from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import pandas as pd

from alphascope.alerts import AlertDispatcher, AlertRuleEngine, TelegramNotifier


class DummyResponse:
    def __init__(self, status_code: int = 200) -> None:
        self.status_code = status_code

    def raise_for_status(self) -> None:
        return None


def test_telegram_notifier_posts_expected_payload() -> None:
    captured: dict[str, object] = {}

    def fake_post(url: str, *, json: dict[str, object], timeout: int) -> DummyResponse:
        captured["url"] = url
        captured["json"] = json
        captured["timeout"] = timeout
        return DummyResponse()

    notifier = TelegramNotifier("token", "chat", enabled=True, timeout=12, post_func=fake_post)
    result = notifier.send_message("hello")

    assert result.delivered is True
    assert captured["url"] == "https://api.telegram.org/bottoken/sendMessage"
    assert captured["json"] == {
        "chat_id": "chat",
        "text": "hello",
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }
    assert captured["timeout"] == 12


def test_telegram_notifier_skips_when_disabled() -> None:
    notifier = TelegramNotifier("token", "chat", enabled=False)

    result = notifier.send_message("hello")

    assert result.delivered is False
    assert result.error == "telegram alerts disabled"


def test_alert_rule_engine_detects_new_top_ranking() -> None:
    ranking = pd.DataFrame(
        [
            {"symbol": "BTCUSDT", "score": 0.91, "rank": 1},
            {"symbol": "ETHUSDT", "score": 0.74, "rank": 2},
        ]
    )

    decision = AlertRuleEngine().new_top_ranking(
        ranking,
        previous_symbol="ETHUSDT",
        previous_score=0.80,
        min_score_delta=0.01,
    )

    assert decision.triggered is True
    assert decision.payload["symbol"] == "BTCUSDT"


def test_alert_rule_engine_detects_heartbeat_issue() -> None:
    runtime_status = {
        "heartbeat": {"timestamp": "2026-03-26T10:00:00+00:00"},
        "daemon": {"status": "running"},
        "recovery": {"issues": [{"code": "stale_heartbeat"}]},
    }

    decision = AlertRuleEngine().heartbeat_lost(runtime_status)

    assert decision.triggered is True
    assert decision.payload["issue_code"] == "stale_heartbeat"


def _make_local_test_dir(name: str) -> Path:
    path = Path("data/runtime/test_runtime") / f"{name}_{uuid4().hex}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_alert_dispatcher_persists_history_and_state() -> None:
    test_dir = _make_local_test_dir("telegram_alerts")
    dispatcher = AlertDispatcher(
        telegram=TelegramNotifier("token", "chat", post_func=lambda *args, **kwargs: DummyResponse()),
        history_path=test_dir / "alerts.jsonl",
        state_path=test_dir / "alerts_state.json",
    )
    ranking = pd.DataFrame([{"symbol": "BTCUSDT", "score": 0.9, "rank": 1}])

    record = dispatcher.top_ranking_changed(ranking)

    assert record is not None
    assert record.delivered is True
    history_lines = (test_dir / "alerts.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(history_lines) == 1
    payload = json.loads(history_lines[0])
    assert payload["alert_type"] == "new_top_ranking"
    state = json.loads((test_dir / "alerts_state.json").read_text(encoding="utf-8"))
    assert state["last_top_symbol"] == "BTCUSDT"
