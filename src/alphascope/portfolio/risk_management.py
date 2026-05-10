from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class PortfolioRiskConfig:
    max_risk_per_trade: float = 0.02
    max_portfolio_exposure: float = 0.30
    max_drawdown: float = 0.15
    max_loss_per_asset: float = 0.10
    max_open_positions: int = 5


class RiskManager:
    def __init__(self, config: PortfolioRiskConfig | None = None):
        self.config = config or PortfolioRiskConfig()

    def validate_new_position(
        self,
        allocation_amount: float,
        total_equity: float,
        current_exposure: float,
        open_positions: int,
        daily_drawdown: float = 0.0,
        asset_loss: float = 0.0,
    ) -> tuple[bool, str]:
        if total_equity <= 0:
            return False, "total_equity_unavailable"
        if allocation_amount > total_equity * self.config.max_risk_per_trade:
            return False, "trade_risk_exceeded"
        projected_exposure = current_exposure + (allocation_amount / total_equity)
        if projected_exposure > self.config.max_portfolio_exposure:
            return False, "portfolio_exposure_exceeded"
        if open_positions >= self.config.max_open_positions:
            return False, "max_open_positions_reached"
        if daily_drawdown >= self.config.max_drawdown:
            return False, "daily_drawdown_exceeded"
        if asset_loss >= self.config.max_loss_per_asset:
            return False, "asset_loss_exceeded"
        return True, "approved"

    def compute_drawdown(self, peak_equity: float, current_equity: float) -> float:
        if peak_equity <= 0:
            return 0.0
        return max(0.0, (peak_equity - current_equity) / peak_equity)
