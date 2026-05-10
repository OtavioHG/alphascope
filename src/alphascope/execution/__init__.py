"""Execution package."""

from alphascope.execution.trader_selector import (
    build_trader,
    log_trader_startup,
    paper_trading_disabled,
    selected_trader_name,
    should_use_live_trader,
)

__all__ = [
    "build_trader",
    "log_trader_startup",
    "paper_trading_disabled",
    "selected_trader_name",
    "should_use_live_trader",
]
