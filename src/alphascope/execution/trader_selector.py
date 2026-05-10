from __future__ import annotations

from pathlib import Path
from typing import Any

from alphascope.alerts import AlertDispatcher
from alphascope.config.settings import settings
from alphascope.execution.live_trader import LiveTrader
from alphascope.execution.paper_trader import PaperTrader
from alphascope.storage.repositories import StorageRepository


def should_use_live_trader() -> bool:
    mode = settings.live_trading_mode.strip().lower()
    return settings.live_trading_enabled and mode != "paper"


def selected_trader_name() -> str:
    return "LiveTrader" if should_use_live_trader() else "PaperTrader"


def paper_trading_disabled() -> bool:
    return selected_trader_name() == "LiveTrader"


def build_trader(
    *,
    repository: StorageRepository | None = None,
    client: Any | None = None,
    alert_dispatcher: AlertDispatcher | None = None,
    state_path: Path | None = None,
) -> LiveTrader | PaperTrader:
    if should_use_live_trader():
        return LiveTrader(
            client=client,
            repository=repository,
            alert_dispatcher=alert_dispatcher,
            state_path=state_path,
        )
    return PaperTrader(
        repository=repository,
        initial_cash=settings.paper_initial_cash,
    )


def log_trader_startup(logger: Any, trader: LiveTrader | PaperTrader) -> None:
    logger.info("LIVE_TRADING_ENABLED=%s", settings.live_trading_enabled)
    logger.info("LIVE_TRADING_MODE=%s", settings.live_trading_mode)
    logger.info("Trader selecionado: %s", trader.__class__.__name__)
    logger.info("PAPER_INITIAL_CASH=%s", settings.paper_initial_cash)
    logger.info("MAX_OPEN_TRADES=%s", settings.max_open_trades)
