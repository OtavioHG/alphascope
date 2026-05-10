from __future__ import annotations

from unittest.mock import patch

from alphascope.alerts.telegram_command_listener import TelegramCommandContext, TelegramCommandListener


class StubRepository:
    def get_trade_executions(self, status: str | None = None):
        return []

    def get_open_positions(self):
        import pandas as pd
        return pd.DataFrame()

    def get_latest_ranking(self, interval: str):
        import pandas as pd
        return pd.DataFrame()

    def get_latest_snapshot(self):
        return {}

    def get_daily_performance(self):
        return {}

    def get_audit_events(self, limit: int = 10):
        import pandas as pd
        return pd.DataFrame([
            {
                "action": "multi_agent_decision",
                "target": "BTCUSDT",
                "payload_json": {
                    "symbol": "BTCUSDT",
                    "timeframe": "1h",
                    "decision": "BUY",
                    "final_score": 0.81,
                    "consensus": "3 of 4 agents agreed",
                    "reasoning": "Strong alignment",
                    "execution_action": "place_order",
                },
            }
        ])


class StubRuntimeStatus:
    def get_status(self, *, interval: str | None = None):
        return {"daemon": {"status": "running"}, "heartbeat": {"status": "running"}, "latest_ranking": {}, "latest_snapshot": {}, "jobs": {}, "recovery": {"issues": []}}


def test_telegram_listener_returns_multi_agent_last_decision_message() -> None:
    listener = TelegramCommandListener(repository=StubRepository(), runtime_status=StubRuntimeStatus())
    message = listener.handle_command(TelegramCommandContext(chat_id="1", text="/ma_last", update_id=1))
    assert "Última decisão multiagente" in message
    assert "BTCUSDT" in message


def test_telegram_listener_returns_multi_agent_status_message() -> None:
    class StubMultiAgentRuntime:
        def status(self):
            return {
                "last_symbol": "BTCUSDT",
                "last_timeframe": "1h",
                "last_decision": "BUY",
                "last_score": 0.82,
                "updated_at": "2026-01-01T00:00:00+00:00",
                "cache": {"backend": "InMemoryRedisClient"},
                "heartbeat": {"status": "running"},
                "scheduler": {"job_count": 2},
                "symbols": {
                    "BTCUSDT": {"symbol": "BTCUSDT", "decision": "BUY", "final_score": 0.82, "execution_action": "place_order", "updated_at": "2026-01-01T00:00:00+00:00"},
                    "ETHUSDT": {"symbol": "ETHUSDT", "decision": "HOLD", "final_score": 0.51, "execution_action": "block_trade", "updated_at": "2026-01-01T00:01:00+00:00"},
                },
            }

        def close(self):
            return None

    with patch("alphascope.alerts.telegram_command_listener.MultiAgentRuntime", StubMultiAgentRuntime):
        listener = TelegramCommandListener(repository=StubRepository(), runtime_status=StubRuntimeStatus())
        message = listener.handle_command(TelegramCommandContext(chat_id="1", text="/ma_status", update_id=2))
    assert "Status multiagente" in message
    assert "BTCUSDT" in message
    assert "ETHUSDT" in message


def test_telegram_listener_runs_multi_agent_command() -> None:
    class StubMultiAgentRuntime:
        def run_cycle(self, *, symbol: str, timeframe: str, mode: str = "paper", send_telegram: bool = True):
            return {
                "symbol": symbol,
                "timeframe": timeframe,
                "supervisor": {
                    "decision": "BUY",
                    "final_score": 0.84,
                    "consensus": "3 of 4 agents agreed",
                    "reasoning": "Aligned signals",
                },
                "execution": {"action": "place_order"},
            }

        def close(self):
            return None

    with patch("alphascope.alerts.telegram_command_listener.MultiAgentRuntime", StubMultiAgentRuntime):
        listener = TelegramCommandListener(repository=StubRepository(), runtime_status=StubRuntimeStatus())
        message = listener.handle_command(TelegramCommandContext(chat_id="1", text="/ma_run BTCUSDT 1h", update_id=3))
    assert "Última decisão multiagente" in message
    assert "place_order" in message
