from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import pytest
import requests

from alphascope.alerts.telegram_command_listener import TelegramCommandContext, TelegramCommandListener
from alphascope.alerts.telegram_command_templates import positions_message, status_message
from alphascope.alerts.telegram_notifier import TelegramNotifier
from alphascope.config.runtime_updates import RuntimeSettingsManager
from alphascope.config.settings import settings


class FakeTelegramResponse:
    def __init__(self, payload: dict[str, Any], status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return self._payload


class FakeNotifier:
    def __init__(self) -> None:
        self.messages: list[tuple[str | None, str]] = []
        self.enabled = True

    def send_message(self, message: str, *, chat_id: str | None = None):  # type: ignore[no-untyped-def]
        self.messages.append((chat_id, message))
        return type("Result", (), {"delivered": True, "chunks_sent": 1, "error": None})()


class FakeRuntimeStatus:
    def get_status(self, *, interval: str | None = None) -> dict[str, Any]:
        del interval
        return {
            "continuous_pipeline": {"last_cycle_finished_at": "2026-04-11T10:00:00+00:00"},
            "apis": settings.api_status_summary(),
        }


class FakeRepository:
    def __init__(self) -> None:
        self.open_positions: dict[str, dict[str, object]] = {}
        self.saved_trades: list[dict[str, object]] = []
        self.snapshots: list[dict[str, object]] = []
        self.rankings = pd.DataFrame(
            [
                {"symbol": "BTCUSDT", "score": 0.91, "rank": 1, "market_regime": "uptrend"},
                {"symbol": "ETHUSDT", "score": 0.77, "rank": 2, "market_regime": "uptrend"},
            ]
        )
        self.candles = {
            "BTCUSDT": pd.DataFrame([{"close": 100.0}]),
            "ETHUSDT": pd.DataFrame([{"close": 80.0}]),
        }

    def get_open_positions(self) -> pd.DataFrame:
        return pd.DataFrame(self.open_positions.values())

    def get_open_position(self, symbol: str) -> dict[str, object] | None:
        return self.open_positions.get(symbol.upper())

    def get_trade_executions(self, **kwargs: Any) -> pd.DataFrame:
        frame = pd.DataFrame(self.saved_trades)
        status = kwargs.get("status")
        if status and not frame.empty:
            frame = frame.loc[frame.get("status", pd.Series(dtype=str)) == status]
        return frame.reset_index(drop=True)

    def save_trades(self, trades: list[dict[str, object]]) -> int:
        self.saved_trades.extend(dict(trade) for trade in trades)
        for trade in trades:
            symbol = str(trade["symbol"]).upper()
            if str(trade["side"]).upper() == "BUY":
                self.open_positions[symbol] = {
                    "symbol": symbol,
                    "quantity": float(trade["quantity"]),
                    "entry_price": float(trade["price"]),
                    "current_price": float(trade["price"]),
                    "unrealized_pnl": 0.0,
                    "stop_price": 95.0,
                    "take_profit_price": 110.0,
                }
            else:
                self.open_positions.pop(symbol, None)
        return len(trades)

    def open_trade_history(self, payload: dict[str, object]) -> str:
        self.saved_trades.append(dict(payload))
        return str(payload.get("trade_id", "trade-id"))

    def close_latest_open_trade(
        self,
        *,
        symbol: str,
        reason_closed: str,
        exit_price: float,
        fees_paid: float,
        notes_json: dict[str, object],
    ) -> int:
        self.saved_trades.append(
            {
                "symbol": symbol,
                "status": "CLOSED",
                "reason_closed": reason_closed,
                "exit_price": exit_price,
                "fees_paid": fees_paid,
                "notes_json": notes_json,
            }
        )
        self.open_positions.pop(symbol.upper(), None)
        return 1

    def update_open_trade_history_metrics(self, symbol: str, price: float) -> int:
        position = self.open_positions.get(symbol.upper())
        if position is not None:
            position["current_price"] = price
        return 1

    def save_snapshot(self, snapshot: dict[str, object]) -> int:
        self.snapshots.append(dict(snapshot))
        return 1

    def get_latest_snapshot(self) -> dict[str, object] | None:
        return self.snapshots[-1] if self.snapshots else {
            "equity": 1000.0,
            "cash": 1000.0,
            "realized_pnl": 0.0,
            "unrealized_pnl": 0.0,
            "positions_json": {},
        }

    def get_latest_ranking(self, interval: str) -> pd.DataFrame:
        del interval
        return self.rankings.copy()

    def get_daily_performance(self) -> dict[str, object]:
        return {"realized_pnl": 12.5, "win_rate": 0.6, "total_trades": 5, "max_drawdown": 0.04}

    def get_latest_account_snapshot(self) -> dict[str, object]:
        return {"exposure_pct": 0.0}

    def get_candles(self, symbol: str, interval: str, limit: int | None = None) -> pd.DataFrame:
        del interval, limit
        return self.candles.get(symbol.upper(), pd.DataFrame())


@pytest.fixture(autouse=True)
def stable_telegram_settings() -> None:
    overrides = {
        "telegram_enabled": True,
        "enable_telegram_alerts": True,
        "telegram_bot_token": "token",
        "telegram_chat_id": "123",
        "request_timeout": 2,
        "request_retries": 2,
        "live_trading_enabled": False,
        "live_trading_mode": "paper",
        "symbols": "BTCUSDT,ETHUSDT",
        "max_open_trades": 2,
        "paper_initial_cash": 1000.0,
        "paper_max_positions": 5,
        "paper_fee_rate": 0.0,
        "default_interval": "1h",
    }
    original = {name: getattr(settings, name) for name in overrides}
    for name, value in overrides.items():
        object.__setattr__(settings, name, value)
    try:
        yield
    finally:
        for name, value in original.items():
            object.__setattr__(settings, name, value)


def _listener(
    *,
    repository: FakeRepository | None = None,
    notifier: FakeNotifier | None = None,
    get_func: Any | None = None,
    env_path: Path | None = None,
) -> TelegramCommandListener:
    return TelegramCommandListener(
        repository=repository or FakeRepository(),  # type: ignore[arg-type]
        notifier=notifier,  # type: ignore[arg-type]
        runtime_status=FakeRuntimeStatus(),  # type: ignore[arg-type]
        settings_manager=RuntimeSettingsManager(env_path=env_path),
        get_func=get_func,
        sleep_func=lambda _: None,
    )


def _make_local_env_dir(name: str) -> Path:
    path = Path("data/runtime/test_runtime") / name
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_listener_bootstraps_and_ignores_duplicate_updates() -> None:
    notifier = FakeNotifier()
    responses = [
        FakeTelegramResponse({"result": [{"update_id": 10, "message": {"chat": {"id": "123"}, "text": "/ping"}}]}),
        FakeTelegramResponse({"result": [{"update_id": 11, "message": {"chat": {"id": "123"}, "text": "/ping"}}]}),
        FakeTelegramResponse({"result": [{"update_id": 11, "message": {"chat": {"id": "123"}, "text": "/ping"}}]}),
    ]

    def fake_get(*args: Any, **kwargs: Any) -> FakeTelegramResponse:
        del args, kwargs
        return responses.pop(0)

    listener = _listener(notifier=notifier, get_func=fake_get)
    assert listener.poll_updates() == 0
    assert listener.poll_updates() == 1
    assert listener.poll_updates() == 0
    assert notifier.messages == [("123", "pong")]


def test_listener_retries_get_updates_after_timeout() -> None:
    notifier = FakeNotifier()
    calls = {"count": 0}

    def fake_get(*args: Any, **kwargs: Any) -> FakeTelegramResponse:
        del args, kwargs
        calls["count"] += 1
        if calls["count"] == 1:
            raise requests.Timeout("boom")
        return FakeTelegramResponse({"result": []})

    listener = _listener(notifier=notifier, get_func=fake_get)
    assert listener.poll_updates() == 0
    assert calls["count"] == 2


def test_status_and_positions_templates_are_formatted() -> None:
    formatted_status = status_message(
        {
            "app_env": "production",
            "mode": "paper",
            "open_trades": 1,
            "open_positions": 1,
            "monitored_coins": 2,
            "last_ranking": "BTCUSDT score=0.9100",
            "last_cycle": "2026-04-11T10:00:00+00:00",
            "telegram_state": "enabled",
            "api_state": "5/6 enabled",
        }
    )
    formatted_positions = positions_message(
        [
            {
                "symbol": "BTCUSDT",
                "quantity": 0.1,
                "entry_price": 100.0,
                "current_price": 101.0,
                "unrealized_pnl": 0.1,
                "stop_price": 98.0,
                "take_profit_price": 104.0,
            }
        ]
    )

    assert "📊 Status operacional AlphaScope" in formatted_status
    assert "APP_ENV: production" in formatted_status
    assert "BTCUSDT" in formatted_positions
    assert "entry=100.000000" in formatted_positions


def test_start_and_help_messages_are_operator_friendly() -> None:
    listener = _listener()

    start_reply = listener.handle_command(TelegramCommandContext(chat_id="123", text="/start", update_id=1))
    help_reply = listener.handle_command(TelegramCommandContext(chat_id="123", text="/help", update_id=2))

    assert "AlphaScope conectado com sucesso" in start_reply
    assert "Modo atual" in start_reply
    assert "Central de comandos AlphaScope" in help_reply
    assert "Execução manual" in help_reply


def test_setmaxtrades_updates_runtime_and_env() -> None:
    env_path = _make_local_env_dir("telegram_listener_env_maxtrades") / ".env"
    env_path.write_text("MAX_OPEN_TRADES=2\n", encoding="utf-8")
    listener = _listener(env_path=env_path)

    reply = listener.handle_command(TelegramCommandContext(chat_id="123", text="/setmaxtrades 3", update_id=1))

    assert "MAX_OPEN_TRADES atualizado para 3" in reply
    assert settings.max_open_trades == 3
    assert "MAX_OPEN_TRADES=3" in env_path.read_text(encoding="utf-8")


def test_manual_buy_and_sell_all_in_paper_mode() -> None:
    repository = FakeRepository()
    listener = _listener(repository=repository)

    buy_reply = listener.handle_command(TelegramCommandContext(chat_id="123", text="/buy BTCUSDT", update_id=1))
    first_sellall_reply = listener.handle_command(TelegramCommandContext(chat_id="123", text="/sellall", update_id=2))
    confirm_reply = listener.handle_command(TelegramCommandContext(chat_id="123", text="/sellall confirm", update_id=3))

    assert "Compra executada em paper" in buy_reply
    assert "Confirmacao necessaria" in first_sellall_reply
    assert "Posicoes fechadas: 1" in confirm_reply
    assert repository.get_open_positions().empty


def test_manual_sell_in_paper_mode() -> None:
    repository = FakeRepository()
    listener = _listener(repository=repository)

    listener.handle_command(TelegramCommandContext(chat_id="123", text="/buy BTCUSDT", update_id=1))
    sell_reply = listener.handle_command(TelegramCommandContext(chat_id="123", text="/sell BTCUSDT", update_id=2))

    assert "Venda executada em paper" in sell_reply
    assert repository.get_open_positions().empty


def test_setmode_live_requires_confirmation() -> None:
    env_path = _make_local_env_dir("telegram_listener_env_mode") / ".env"
    env_path.write_text("LIVE_TRADING_MODE=paper\nLIVE_TRADING_ENABLED=false\n", encoding="utf-8")
    listener = _listener(env_path=env_path)

    first = listener.handle_command(TelegramCommandContext(chat_id="123", text="/setmode live", update_id=1))
    second = listener.handle_command(TelegramCommandContext(chat_id="123", text="/setmode live confirm", update_id=2))

    assert "Confirmacao necessaria" in first
    assert "Modo alterado para live" in second
    assert settings.live_trading_mode == "live"
    env_text = env_path.read_text(encoding="utf-8")
    assert "LIVE_TRADING_MODE=live" in env_text
    assert "LIVE_TRADING_ENABLED=true" in env_text


def test_telegram_notifier_retries_and_splits_messages() -> None:
    attempts = {"count": 0}

    class DummyResponse:
        status_code = 200

        def raise_for_status(self) -> None:
            return None

    def fake_post(url: str, *, json: dict[str, object], timeout: int) -> DummyResponse:
        del url, timeout
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise requests.Timeout("first fail")
        assert len(str(json["text"])) <= 10
        return DummyResponse()

    notifier = TelegramNotifier("token", "chat", timeout=1, retries=2, max_message_length=10, post_func=fake_post)
    result = notifier.send_message("1234567890\nabcdefghij")
    notifier.close()

    assert result.delivered is True
    assert result.chunks_sent == 2
    assert attempts["count"] == 3
