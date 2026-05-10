from __future__ import annotations

from typing import Any

from alphascope.platform.config_loader import PlatformConfigLoader
from alphascope.platform.execution_safety import ExecutionSafetyGuard
from alphascope.platform.exit_engine import ExitDecisionEngine
from alphascope.platform.quant_models import (
    ExchangeFilters,
    OrderIntent,
    PortfolioRiskState,
    PositionContext,
    SignalContext,
)
from alphascope.platform.risk_engine import AdvancedRiskEngine
from alphascope.platform.signal_engine import AdvancedSignalEngine


class AlphaPlatformService:
    """Facade used by CLI, Telegram and API layers."""

    def __init__(self) -> None:
        self.config = PlatformConfigLoader().load()
        self.signal_engine = AdvancedSignalEngine(self.config)
        self.exit_engine = ExitDecisionEngine(self.config)
        self.risk_engine = AdvancedRiskEngine(self.config)
        self.execution_guard = ExecutionSafetyGuard(self.config)

    def evaluate_entry(self, payload: dict[str, Any]) -> dict[str, Any]:
        decision = self.signal_engine.evaluate(SignalContext(**payload))
        return decision.__dict__

    def evaluate_exit(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        decisions = self.exit_engine.evaluate(PositionContext(**payload))
        return [decision.__dict__ for decision in decisions]

    def evaluate_risk(self, payload: dict[str, Any]) -> dict[str, Any]:
        decision = self.risk_engine.evaluate(PortfolioRiskState(**payload))
        return decision.__dict__

    def validate_order(self, payload: dict[str, Any], filters: dict[str, Any]) -> dict[str, Any]:
        decision = self.execution_guard.validate(OrderIntent(**payload), ExchangeFilters(**filters))
        return decision.__dict__
