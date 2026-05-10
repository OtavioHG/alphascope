"""Risk management agent."""

from __future__ import annotations

from alphascope.agents.schemas import AgentOutput, MultiAgentContext
from alphascope.agents.scoring_engine import ScoringEngine
from alphascope.config.settings import settings


class RiskManagementAgent:

    def analyze(self, context: MultiAgentContext) -> AgentOutput:
        account = context.account or {}
        daily = context.daily_performance or {}
        open_positions = context.open_positions or []
        features = context.features or {}

        exposure_pct = float(account.get("exposure_pct", 0.0) or 0.0)
        open_count = int(account.get("open_positions", len(open_positions)) or len(open_positions))
        consecutive_losses = int(daily.get("consecutive_losses", 0) or 0)
        drawdown = float(daily.get("max_drawdown", 0.0) or 0.0)
        volatility = float(features.get("volatility", 0.0) or 0.0)
        total_balance = float(account.get("total_balance", 1000.0) or 1000.0)

        risk_penalty = 0.0
        reasons: list[str] = []
        if exposure_pct > 0.35:
            risk_penalty += 0.25
            reasons.append("Exposição acima de 35%")
        if open_count >= 4:
            risk_penalty += 0.15
            reasons.append("Muitas posições abertas")
        if consecutive_losses >= 3:
            risk_penalty += 0.20
            reasons.append("Sequência de perdas recente")
        if drawdown > 0.08:
            risk_penalty += 0.20
            reasons.append("Drawdown acima do limite confortável")
        if volatility > 0.08:
            risk_penalty += 0.15
            reasons.append("Volatilidade do ativo elevada")

        risk_score = max(0.0, min(1.0, 0.15 + risk_penalty))
        allow_trade = risk_score < 0.60
        position_size_pct = max(0.005, min(0.03, 0.02 - risk_penalty * 0.015))
        stop_loss_pct = max(0.008, min(0.025, 0.012 + volatility * 0.10 + risk_penalty * 0.01))
        take_profit_pct = max(stop_loss_pct * 1.5, min(0.05, stop_loss_pct * 2.0 + 0.005))

        signal = "buy" if allow_trade else "sell"
        confidence = max(0.45, min(0.95, 0.55 + risk_penalty))
        model_config = settings.multi_agent_model_registry["risk"]
        return AgentOutput(
            agent="risk_manager",
            signal=signal if allow_trade else "hold",
            confidence=confidence,
            score=1.0 - risk_score,
            reasoning=", ".join(reasons) if reasons else "Exposição, drawdown e volatilidade sob controle",
            metadata={
                "allow_trade": allow_trade,
                "risk_score": round(risk_score, 4),
                "position_size_pct": round(position_size_pct, 4),
                "stop_loss_pct": round(stop_loss_pct, 4),
                "take_profit_pct": round(take_profit_pct, 4),
                "total_balance": round(total_balance, 4),
                "inference_backend": "local_risk_proxy",
                "external_llm_available": settings.external_llm_available,
                "configured_primary_model": model_config["primary"],
                "configured_fallback_model": model_config["fallback"],
            },
            model_name=str(model_config["active"]),
            fallback_used=not bool(model_config["external"]),
        )
