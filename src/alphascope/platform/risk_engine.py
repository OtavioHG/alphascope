from __future__ import annotations

from alphascope.platform.config_models import PlatformConfig, RiskProfile
from alphascope.platform.quant_models import PortfolioRiskState, RiskDecision


class AdvancedRiskEngine:
    def __init__(self, config: PlatformConfig) -> None:
        self.config = config

    def evaluate(self, state: PortfolioRiskState) -> RiskDecision:
        recommended_position_pct = min(self.config.risk.max_position_size_pct, self._profile_position_cap())

        if state.daily_trades >= self.config.risk.max_trades_per_day:
            return RiskDecision(False, "daily_trade_limit", 0.0, pause_trading=True)
        if state.consecutive_losses >= self.config.risk.max_consecutive_losses:
            return RiskDecision(False, "consecutive_losses_limit", 0.0, pause_trading=True)
        if state.daily_pnl_pct <= -self.config.risk.daily_drawdown_pause_pct:
            return RiskDecision(False, "daily_drawdown_pause", 0.0, pause_trading=True)
        if state.daily_pnl_pct <= -self.config.risk.emergency_drawdown_pct:
            return RiskDecision(False, "emergency_drawdown", 0.0, pause_trading=True, trigger_emergency_exit=True)
        if state.open_positions >= self.config.risk.max_simultaneous_positions:
            return RiskDecision(False, "max_simultaneous_positions", 0.0)
        if state.portfolio_exposure_pct >= self.config.risk.max_portfolio_exposure_pct:
            return RiskDecision(False, "portfolio_exposure_limit", 0.0)
        if state.symbol_exposure_pct >= self.config.risk.max_symbol_exposure_pct:
            return RiskDecision(False, "symbol_exposure_limit", 0.0)
        if state.candidate_volatility >= self.config.risk.volatile_asset_threshold:
            return RiskDecision(False, "asset_too_volatile", 0.0)
        if state.free_cash / max(state.equity, 1e-9) <= self.config.risk.min_cash_reserve_pct:
            return RiskDecision(False, "cash_reserve_protection", 0.0)

        if state.consecutive_losses > 0:
            recommended_position_pct *= self.config.risk.reduce_size_after_loss_factor
        return RiskDecision(True, "approved", recommended_position_pct)

    def _profile_position_cap(self) -> float:
        profile_caps = {
            RiskProfile.conservative: 0.04,
            RiskProfile.moderate: 0.08,
            RiskProfile.aggressive: 0.12,
            RiskProfile.sniper: 0.06,
            RiskProfile.scalping: 0.05,
        }
        return profile_caps[self.config.risk.profile]
