from __future__ import annotations

import pytest

from alphascope.execution.execution_guard import ExecutionConstraint, ExecutionGuard
from alphascope.execution.reconciliation import ReconciliationEngine
from alphascope.execution.retry_engine import RetryEngine


def test_execution_guard_rejects_out_of_limits_trade() -> None:
    guard = ExecutionGuard(ExecutionConstraint(max_exposure=0.3, min_liquidity=1000.0, max_volatility=0.1, max_trade_risk=0.02))
    approved, reason = guard.validate(exposure=0.4, liquidity=5000.0, volatility=0.05, trade_risk=0.01)
    assert approved is False
    assert "exposure" in reason


def test_reconciliation_detects_position_differences() -> None:
    result = ReconciliationEngine().compare_positions(
        [{"symbol": "BTCUSDT"}, {"symbol": "ETHUSDT"}],
        [{"symbol": "BTCUSDT"}, {"symbol": "SOLUSDT"}],
    )
    assert len(result["matched"]) == 1
    assert result["missing_on_exchange"][0]["symbol"] == "ETHUSDT"
    assert result["missing_internal"][0]["symbol"] == "SOLUSDT"


def test_retry_engine_retries_and_returns_value() -> None:
    state = {"attempts": 0}

    def flaky() -> str:
        state["attempts"] += 1
        if state["attempts"] < 3:
            raise ValueError("temporary")
        return "ok"

    assert RetryEngine(retries=3, backoff_seconds=0.0).run(flaky) == "ok"

    with pytest.raises(ValueError):
        RetryEngine(retries=2, backoff_seconds=0.0).run(lambda: (_ for _ in ()).throw(ValueError("boom")))
