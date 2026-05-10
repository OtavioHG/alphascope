"""Schemas shared by AlphaScope multi-agent components."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Literal

from alphascope.utils.time import utc_now

SignalValue = Literal["buy", "sell", "hold"]
DecisionValue = Literal["BUY", "SELL", "HOLD"]


@dataclass(slots=True)
class AgentOutput:
    agent: str
    signal: SignalValue
    confidence: float
    reasoning: str
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)
    model_name: str = "local"
    fallback_used: bool = False
    created_at: datetime = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["created_at"] = self.created_at.isoformat()
        return payload


@dataclass(slots=True)
class DebateMessage:
    round_id: int
    speaker: str
    stance: str
    message: str
    target_agent: str | None = None
    created_at: datetime = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["created_at"] = self.created_at.isoformat()
        return payload


@dataclass(slots=True)
class ConsensusDecision:
    agent: str
    decision: DecisionValue
    final_score: float
    consensus: str
    reasoning: str
    approvals: int
    rejections: int
    weights: dict[str, float] = field(default_factory=dict)
    component_scores: dict[str, float] = field(default_factory=dict)
    created_at: datetime = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["created_at"] = self.created_at.isoformat()
        return payload


@dataclass(slots=True)
class ExecutionPlan:
    agent: str
    action: str
    symbol: str
    side: str
    size_usd: float
    stop_loss: float
    take_profit: float
    reasoning: str
    cooldown_seconds: int = 0
    created_at: datetime = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["created_at"] = self.created_at.isoformat()
        return payload


@dataclass(slots=True)
class MultiAgentContext:
    symbol: str
    timeframe: str
    candles: list[dict[str, Any]]
    features: dict[str, Any]
    ranking: dict[str, Any]
    account: dict[str, Any]
    open_positions: list[dict[str, Any]]
    daily_performance: dict[str, Any]
    market_snapshots: list[dict[str, Any]] = field(default_factory=list)
    feature_snapshots: list[dict[str, Any]] = field(default_factory=list)
    model_predictions: list[dict[str, Any]] = field(default_factory=list)
    recent_consensus: list[dict[str, Any]] = field(default_factory=list)
    recent_agent_decisions: list[dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["created_at"] = self.created_at.isoformat()
        return payload


@dataclass(slots=True)
class MultiAgentRunResult:
    symbol: str
    timeframe: str
    market_output: AgentOutput
    news_output: AgentOutput
    risk_output: AgentOutput
    memory_output: AgentOutput
    debate: list[DebateMessage]
    supervisor: ConsensusDecision
    execution: ExecutionPlan
    mode: str
    runtime_event: dict[str, Any]
    exported_training_paths: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "market_output": self.market_output.to_dict(),
            "news_output": self.news_output.to_dict(),
            "risk_output": self.risk_output.to_dict(),
            "memory_output": self.memory_output.to_dict(),
            "debate": [item.to_dict() for item in self.debate],
            "supervisor": self.supervisor.to_dict(),
            "execution": self.execution.to_dict(),
            "mode": self.mode,
            "runtime_event": self.runtime_event,
            "exported_training_paths": list(self.exported_training_paths),
        }
