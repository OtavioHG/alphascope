"""Supervisor agent facade."""

from __future__ import annotations

from alphascope.agents.consensus_engine import ConsensusEngine
from alphascope.agents.schemas import AgentOutput, ConsensusDecision


class SupervisorAgent:
    def __init__(self, repository) -> None:
        self.consensus_engine = ConsensusEngine(repository)

    def supervise(
        self,
        *,
        market: AgentOutput,
        news: AgentOutput,
        risk: AgentOutput,
        memory: AgentOutput,
    ) -> ConsensusDecision:
        return self.consensus_engine.build_decision(market=market, news=news, risk=risk, memory=memory)
