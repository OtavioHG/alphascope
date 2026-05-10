from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ExecutionConstraint:
    max_exposure: float = 0.30
    min_liquidity: float = 1000.0
    max_volatility: float = 0.15
    max_trade_risk: float = 0.02


class ExecutionGuard:
    def __init__(self, constraint: ExecutionConstraint | None = None):
        self.constraint = constraint or ExecutionConstraint()

    def validate(self, exposure: float, liquidity: float, volatility: float, trade_risk: float) -> tuple[bool, str]:
        if exposure > self.constraint.max_exposure:
            return False, "portfolio exposure exceeded"
        if liquidity < self.constraint.min_liquidity:
            return False, "insufficient liquidity"
        if volatility > self.constraint.max_volatility:
            return False, "volatility too high"
        if trade_risk > self.constraint.max_trade_risk:
            return False, "trade risk exceeded"
        return True, "ok"
