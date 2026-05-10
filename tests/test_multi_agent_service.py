from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from alphascope.agents.consensus_engine import ConsensusEngine
from alphascope.agents.learning_engine import MultiAgentLearningEngine
from alphascope.agents.orchestrator import MultiAgentOrchestrator
from alphascope.agents.schemas import AgentOutput
from alphascope.config.settings import settings


def _make_local_test_dir(name: str) -> Path:
    path = Path("data/runtime/test_multi_agent_service") / f"{name}_{uuid4().hex}"
    path.mkdir(parents=True, exist_ok=True)
    return path


class FakeRepository:
    def __init__(self) -> None:
        self.saved_agent_outputs: list[dict] = []
        self.saved_debates: list[dict] = []
        self.saved_consensus: list[dict] = []
        self.saved_audits: list[dict] = []
        self.saved_runtime_events: list[dict] = []
        self.saved_memory: list[tuple[str, dict]] = []
        self.storage = self

    def build_context(self, *, symbol: str, timeframe: str):
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "candles": [{"close": 100.0}],
            "features": {
                "rsi": 55.0,
                "momentum": 0.04,
                "relative_volume": 1.6,
                "ma_short": 102.0,
                "ma_long": 98.0,
                "volatility": 0.03,
                "trend_strength": 0.5,
                "close": 100.0,
            },
            "ranking": {"score": 0.82, "news_score": 0.74, "market_regime": "bullish", "market_sentiment_adjustment": 0.1},
            "account": {"total_balance": 5000.0, "exposure_pct": 0.1, "open_positions": 1},
            "open_positions": [],
            "daily_performance": {"consecutive_losses": 0, "max_drawdown": 0.02},
            "market_snapshots": [{"fear_greed_value": 62.0, "sentiment_score": 0.15}],
            "feature_snapshots": [],
            "model_predictions": [],
            "recent_consensus": [],
            "recent_agent_decisions": [],
        }

    def get_dynamic_weight_multipliers(self):
        return {"nemotron": 1.0, "gpt_oss": 1.0, "minimax": 1.0, "trinity": 1.0}

    def save_agent_output(self, *, symbol: str, timeframe: str, output: dict):
        self.saved_agent_outputs.append(output)

    def save_debate_messages(self, *, symbol: str, timeframe: str, debate: list[dict]):
        self.saved_debates.extend(debate)

    def save_consensus(self, payload: dict, *, symbol: str, timeframe: str):
        self.saved_consensus.append(payload)

    def open_execution_intent(self, *, symbol: str, timeframe: str, execution: dict, consensus: dict):
        self.saved_runtime_events.append({"type": "execution_intent", "execution": execution, "consensus": consensus})

    def save_trade_audit(self, payload: dict):
        self.saved_audits.append(payload)

    def save_audit_event(self, payload: dict):
        self.saved_audits.append(payload)

    def save_runtime_event(self, payload: dict):
        self.saved_runtime_events.append(payload)
        return payload

    def save_memory_entry(self, *, table_name: str, payload: dict):
        self.saved_memory.append((table_name, payload))

    def get_recent_consensus(self, *, symbol: str | None = None, limit: int = 100):
        return []

    def get_recent_agent_decisions(self, *, symbol: str | None = None, limit: int = 100):
        return []

    def get_memory_entries(self, table_name: str, *, limit: int = 100):
        return []

    def get_agent_performance(self, *, limit: int = 200):
        return []


class StaticRepository:
    def get_dynamic_weight_multipliers(self):
        return {"nemotron": 1.0, "gpt_oss": 1.0, "minimax": 1.0, "trinity": 1.0}


def test_consensus_engine_returns_buy_when_components_are_strong() -> None:
    engine = ConsensusEngine(StaticRepository())
    decision = engine.build_decision(
        market=AgentOutput(agent="market_intelligence", signal="buy", confidence=0.9, reasoning="bullish", score=0.92),
        news=AgentOutput(agent="news_sentiment", signal="buy", confidence=0.8, reasoning="positive", score=0.84),
        risk=AgentOutput(agent="risk_manager", signal="buy", confidence=0.7, reasoning="risk ok", score=0.81, metadata={"allow_trade": True}),
        memory=AgentOutput(agent="memory_engine", signal="buy", confidence=0.75, reasoning="history ok", score=0.79),
    )
    assert decision.decision == "BUY"
    assert decision.final_score >= settings.multi_agent_buy_threshold


def test_consensus_engine_returns_hold_between_thresholds() -> None:
    engine = ConsensusEngine(StaticRepository())
    decision = engine.build_decision(
        market=AgentOutput(agent="market_intelligence", signal="hold", confidence=0.50, reasoning="mixed", score=0.50),
        news=AgentOutput(agent="news_sentiment", signal="hold", confidence=0.45, reasoning="neutral", score=0.46),
        risk=AgentOutput(agent="risk_manager", signal="buy", confidence=0.55, reasoning="risk ok", score=0.60, metadata={"allow_trade": True}),
        memory=AgentOutput(agent="memory_engine", signal="hold", confidence=0.42, reasoning="flat", score=0.44),
    )
    assert settings.multi_agent_sell_threshold < decision.final_score < settings.multi_agent_buy_threshold
    assert decision.decision == "HOLD"


def test_orchestrator_runs_end_to_end_with_fake_repository() -> None:
    fake_repo = FakeRepository()
    local_tmp = _make_local_test_dir("orchestrator")
    original_training_dir = settings.training_data_dir
    original_telegram_enabled = settings.telegram_enabled
    object.__setattr__(settings, "data_dir", local_tmp)
    object.__setattr__(settings, "telegram_enabled", False)
    try:
        orchestrator = MultiAgentOrchestrator(repository=fake_repo)
        result = orchestrator.run(symbol="BTCUSDT", timeframe="1h", send_telegram=False, execute_plan=False)
        orchestrator.close()
    finally:
        object.__setattr__(settings, "data_dir", original_training_dir.parent)
        object.__setattr__(settings, "telegram_enabled", original_telegram_enabled)

    assert result.supervisor.decision in {"BUY", "HOLD", "SELL"}
    assert result.execution.agent == "execution"
    assert len(fake_repo.saved_agent_outputs) == 4
    assert len(fake_repo.saved_debates) >= 4
    assert len(fake_repo.saved_consensus) == 1
    assert fake_repo.saved_audits
    assert fake_repo.saved_memory


def test_learning_engine_reports_available_trainers() -> None:
    payload = MultiAgentLearningEngine().available_trainers()
    assert "sklearn" in payload
    assert "xgboost" in payload
    assert "lightgbm" in payload
    assert "catboost" in payload
