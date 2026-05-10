"""Consensus calculation for AlphaScope multi-agent decisions."""

from __future__ import annotations

from alphascope.agents.schemas import AgentOutput, ConsensusDecision
from alphascope.agents.scoring_engine import ScoringEngine
from alphascope.config.settings import settings


class ConsensusEngine:
    def __init__(self, repository) -> None:
        self.repository = repository

    def build_decision(
        self,
        *,
        market: AgentOutput,
        news: AgentOutput,
        risk: AgentOutput,
        memory: AgentOutput,
    ) -> ConsensusDecision:
        dynamic_metrics = self.repository.get_dynamic_weight_multipliers()
        weights = ScoringEngine.rebalance_weights(dynamic_metrics)
        component_scores = {
            "nemotron": ScoringEngine.aggregate_output_scores([market, risk]),
            "gpt_oss": news.score,
            "minimax": 1.0 if risk.metadata.get("allow_trade") else 0.2,
            "trinity": memory.score,
        }
        final_score = sum(component_scores[key] * weights[key] for key in weights)
        if final_score >= settings.multi_agent_buy_threshold:
            decision = "BUY"
        elif final_score <= settings.multi_agent_sell_threshold:
            decision = "SELL"
        else:
            decision = "HOLD"

        raw_signals = [market.signal, news.signal, memory.signal]
        approvals = sum(1 for signal in raw_signals if signal == "buy")
        rejections = sum(1 for signal in raw_signals if signal == "sell")
        consensus = f"{max(approvals, rejections)} of 4 agents agreed"
        reasoning = (
            f"Score final {final_score:.4f} com pesos dinâmicos; mercado={component_scores['nemotron']:.4f}, "
            f"notícias={component_scores['gpt_oss']:.4f}, execução={component_scores['minimax']:.4f}, memória={component_scores['trinity']:.4f}"
        )
        return ConsensusDecision(
            agent="supervisor",
            decision=decision,
            final_score=round(final_score, 6),
            consensus=consensus,
            reasoning=reasoning,
            approvals=approvals,
            rejections=rejections,
            weights={key: round(value, 6) for key, value in weights.items()},
            component_scores={key: round(value, 6) for key, value in component_scores.items()},
        )
