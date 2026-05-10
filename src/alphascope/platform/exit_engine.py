from __future__ import annotations

from alphascope.platform.config_models import PlatformConfig
from alphascope.platform.quant_models import ExitDecision, PositionContext


class ExitDecisionEngine:
    def __init__(self, config: PlatformConfig) -> None:
        self.config = config

    def evaluate(self, position: PositionContext) -> list[ExitDecision]:
        decisions: list[ExitDecision] = []
        pnl_pct = position.pnl_pct

        if pnl_pct >= self.config.exit.break_even_trigger_pct and position.stop_loss_price is not None:
            decisions.append(
                ExitDecision(
                    action="MOVE_STOP",
                    reason="break_even",
                    quantity_pct=0.0,
                    updated_stop_price=max(position.stop_loss_price, position.entry_price),
                )
            )

        if position.trailing_stop_price is not None:
            new_trailing = max(
                position.trailing_stop_price,
                position.current_price * (1.0 - self.config.exit.trailing_stop_pct),
            )
            if new_trailing > position.trailing_stop_price:
                decisions.append(
                    ExitDecision(
                        action="MOVE_STOP",
                        reason="dynamic_trailing_stop",
                        quantity_pct=0.0,
                        updated_stop_price=new_trailing,
                    )
                )

        accumulated = 0.0
        for level, size in zip(
            self.config.exit.partial_take_profit_levels,
            self.config.exit.partial_take_profit_sizes,
            strict=False,
        ):
            accumulated += size
            if pnl_pct >= level and position.realized_partial_pct + 1e-9 < accumulated:
                decisions.append(ExitDecision(action="PARTIAL_SELL", reason=f"take_profit_{int(level * 100)}bp", quantity_pct=size))
                break

        if position.score < self.config.exit.score_exit_threshold:
            decisions.append(ExitDecision(action="CLOSE", reason="score_deterioration"))
        if position.current_rank > self.config.exit.rank_exit_threshold:
            decisions.append(ExitDecision(action="CLOSE", reason="lost_rank_1"))
        if position.best_alternative_score_gap >= self.config.exit.stronger_asset_gap:
            decisions.append(ExitDecision(action="CLOSE", reason="stronger_asset_available"))
        if position.age.total_seconds() >= self.config.exit.max_trade_hours * 3600:
            decisions.append(ExitDecision(action="CLOSE", reason="max_holding_time"))
        if position.momentum_score < self.config.exit.momentum_floor:
            decisions.append(ExitDecision(action="CLOSE", reason="momentum_breakdown"))
        return decisions
