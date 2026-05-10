"""Execution planning agent."""

from __future__ import annotations

from alphascope.agents.schemas import ConsensusDecision, ExecutionPlan
from alphascope.config.settings import settings


class ExecutionAgent:

    def build_plan(self, *, symbol: str, supervisor: ConsensusDecision, risk_metadata: dict[str, float | bool], account: dict[str, object]) -> ExecutionPlan:
        allow_trade = bool(risk_metadata.get("allow_trade", False))
        side = supervisor.decision
        total_balance = float(account.get("total_balance", 1000.0) or 1000.0)
        position_size_pct = float(risk_metadata.get("position_size_pct", 0.01) or 0.01)
        size_usd = round(max(20.0, total_balance * position_size_pct), 2)
        stop_loss_pct = float(risk_metadata.get("stop_loss_pct", 0.015) or 0.015)
        take_profit_pct = float(risk_metadata.get("take_profit_pct", 0.03) or 0.03)
        model_config = settings.multi_agent_model_registry["execution"]
        model_label = str(model_config["active"])

        if supervisor.decision == "HOLD" or not allow_trade:
            return ExecutionPlan(
                agent="execution",
                action="block_trade",
                symbol=symbol,
                side="NONE",
                size_usd=0.0,
                stop_loss=round(stop_loss_pct * 100, 3),
                take_profit=round(take_profit_pct * 100, 3),
                reasoning=f"Trade bloqueado pelo supervisor ou pelo risk manager. policy={model_label}",
                cooldown_seconds=900,
            )
        return ExecutionPlan(
            agent="execution",
            action="place_order",
            symbol=symbol,
            side=side,
            size_usd=size_usd,
            stop_loss=round(stop_loss_pct * 100, 3),
            take_profit=round(take_profit_pct * 100, 3),
            reasoning=f"Trade aprovado pelo supervisor e validado pelo execution agent. policy={model_label}",
            cooldown_seconds=300,
        )
