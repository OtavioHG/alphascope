from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import alphascope.storage.repositories as repositories_module
from alphascope.cli_runtime import _handle_reset_live_state, _handle_show_trader_mode
from alphascope.config.settings import settings
from alphascope.execution.live_trader import LiveTrader
from alphascope.execution.paper_trader import PaperTrader
from alphascope.execution.trader_selector import build_trader, selected_trader_name, should_use_live_trader
from alphascope.storage.database import Base
from alphascope.storage.repositories import StorageRepository
from test_live_trading import FakeClient, FakeRepository


class PaperModeRepository(FakeRepository):
    def get_latest_snapshot(self) -> dict[str, object] | None:
        return None


def _make_local_test_dir(name: str) -> Path:
    path = Path("data/runtime/test_trader_mode") / f"{name}_{uuid4().hex}"
    path.mkdir(parents=True, exist_ok=True)
    return path


@pytest.fixture
def temp_repository(monkeypatch: pytest.MonkeyPatch) -> StorageRepository:
    database_path = _make_local_test_dir("db") / "test_trader_mode.db"
    engine = create_engine(f"sqlite:///{database_path.as_posix()}", future=True)
    testing_session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    Base.metadata.create_all(bind=engine)

    @contextmanager
    def testing_session_scope():
        session = testing_session_local()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    monkeypatch.setattr(repositories_module, "SessionLocal", testing_session_local)
    monkeypatch.setattr(repositories_module, "session_scope", testing_session_scope)
    repository = StorageRepository()
    try:
        yield repository
    finally:
        engine.dispose()


@pytest.fixture
def stable_trader_settings() -> None:
    overrides = {
        "live_trading_enabled": True,
        "live_trading_mode": "live",
        "paper_initial_cash": 10_000.0,
    }
    original = {name: getattr(settings, name) for name in overrides}
    for name, value in overrides.items():
        object.__setattr__(settings, name, value)
    try:
        yield
    finally:
        for name, value in original.items():
            object.__setattr__(settings, name, value)


def test_live_trading_enabled_true_uses_live_trader(stable_trader_settings: None) -> None:
    test_dir = _make_local_test_dir("live_true")
    trader = build_trader(
        repository=FakeRepository(),
        client=FakeClient(),
        state_path=test_dir / "live_state.json",
    )
    assert isinstance(trader, LiveTrader)


def test_live_trading_enabled_false_uses_paper_trader(stable_trader_settings: None) -> None:
    object.__setattr__(settings, "live_trading_enabled", False)
    trader = build_trader(repository=PaperModeRepository(), client=FakeClient())
    assert isinstance(trader, PaperTrader)


def test_live_trading_mode_live_uses_live_trader(stable_trader_settings: None) -> None:
    object.__setattr__(settings, "live_trading_mode", "live")
    test_dir = _make_local_test_dir("mode_live")
    trader = build_trader(
        repository=FakeRepository(),
        client=FakeClient(),
        state_path=test_dir / "live_state_live.json",
    )
    assert isinstance(trader, LiveTrader)
    assert selected_trader_name() == "LiveTrader"
    assert should_use_live_trader() is True


def test_live_trading_mode_paper_uses_paper_trader(stable_trader_settings: None) -> None:
    object.__setattr__(settings, "live_trading_mode", "paper")
    trader = build_trader(repository=PaperModeRepository(), client=FakeClient())
    assert isinstance(trader, PaperTrader)
    assert selected_trader_name() == "PaperTrader"
    assert should_use_live_trader() is False


def test_show_trader_mode_returns_current_selection(
    stable_trader_settings: None,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _handle_show_trader_mode(args=None)  # type: ignore[arg-type]
    captured = capsys.readouterr().out
    assert "LIVE_TRADING_ENABLED=true" in captured
    assert "LIVE_TRADING_MODE=live" in captured
    assert "Trader selecionado=LiveTrader" in captured
    assert "Paper trading desativado=true" in captured


def test_reset_live_state_cleans_positions_and_resets_exposure(
    stable_trader_settings: None,
    temp_repository: StorageRepository,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_file = _make_local_test_dir("reset_state") / "live_state.json"
    monkeypatch.setattr(
        settings.__class__,
        "live_trading_state_file",
        property(lambda self: state_file),
    )

    temp_repository.upsert_open_position(
        {
            "symbol": "DOGEUSDT",
            "quantity": 100.0,
            "entry_price": 0.09,
            "current_price": 0.10,
            "unrealized_pnl": 1.0,
            "stop_price": 0.08,
            "take_profit_price": 0.12,
            "trailing_stop_price": 0.095,
            "order_id": "live-1",
            "mode": "live",
            "status": "OPEN",
            "opened_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }
    )
    temp_repository.save_trade_execution(
        {
            "timestamp": datetime.now(UTC),
            "symbol": "DOGEUSDT",
            "side": "BUY",
            "quantity": 100.0,
            "entry_price": 0.09,
            "exit_price": None,
            "stop_loss_price": 0.08,
            "take_profit_price": 0.12,
            "pnl": 0.0,
            "pnl_pct": 0.0,
            "status": "OPEN",
            "order_id": "live-1",
            "source": "test",
            "mode": "live",
            "confidence_score": 0.8,
            "notes": "",
            "created_at": datetime.now(UTC),
        }
    )
    temp_repository.save_account_snapshot(
        {
            "timestamp": datetime.now(UTC),
            "mode": "live",
            "total_balance": 1000.0,
            "free_balance": 900.0,
            "locked_balance": 100.0,
            "exposure_pct": 0.1,
            "open_positions": 1,
            "open_orders": 1,
            "snapshot_json": {"account": {"balances": []}, "open_positions": [{"symbol": "DOGEUSDT"}], "open_orders": []},
        }
    )

    _handle_reset_live_state(args=None, repository=temp_repository)  # type: ignore[arg-type]
    captured = capsys.readouterr().out

    assert "Resetting live trading state..." in captured
    assert "Open positions removed: 1" in captured
    assert "Stuck trades removed: 1" in captured
    assert "Exposure cache reset" in captured
    assert "Live trading state cleaned successfully" in captured
    assert temp_repository.get_open_positions().empty
    assert temp_repository.get_trade_executions(status="OPEN").empty

    latest_snapshot = temp_repository.get_latest_account_snapshot()
    assert latest_snapshot is not None
    assert latest_snapshot["exposure_pct"] == 0.0
    assert latest_snapshot["open_positions"] == 0
    assert state_file.exists()
