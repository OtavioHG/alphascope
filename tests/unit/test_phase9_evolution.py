from __future__ import annotations

import shutil
from pathlib import Path

import pandas as pd

from alphascope.evolution.degradation_detector import DegradationDetector
from alphascope.evolution.promotion_engine import PromotionEngine
from alphascope.evolution.strategy_lifecycle import StrategyLifecycle
from alphascope.evolution.strategy_registry import StrategyRegistry
from alphascope.evolution.strategy_versioning import StrategyVersioning
from alphascope.governance.decision_log import DecisionLog
from alphascope.research_continuous.regime_performance_tracker import RegimePerformanceTracker
from alphascope.research_continuous.robustness_monitor import RobustnessMonitor
from alphascope.research_continuous.rolling_evaluator import RollingEvaluator


def _base_dir() -> Path:
    base_dir = Path("data/processed/test_phase9_unit")
    if base_dir.exists():
        shutil.rmtree(base_dir)
    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir


def test_strategy_registry_versioning_and_lifecycle() -> None:
    base_dir = _base_dir()
    registry = StrategyRegistry(output_dir=str(base_dir / "lifecycle"))
    versioning = StrategyVersioning(output_dir=str(base_dir / "lifecycle"))
    lifecycle = StrategyLifecycle(registry=registry, output_dir=str(base_dir / "lifecycle"))

    registry.register(
        {
            "strategy_id": "strategy_001",
            "strategy_name": "strategy_001",
            "version": 1,
            "status": "candidate",
        }
    )
    versioning.create_version("strategy_001_v2", "strategy_001", 2, {"buy_threshold": 0.73})
    transitions = lifecycle.transition("strategy_001", "paper_trading", "promotion_thresholds_met")

    loaded = registry.load()
    comparison = versioning.compare_versions("strategy_001_v2", "strategy_001_v2")
    assert "strategy_001" in set(loaded["strategy_id"])
    assert str(loaded.loc[loaded["strategy_id"] == "strategy_001", "status"].iloc[0]) == "paper_trading"
    assert not transitions.empty
    assert comparison["current_version"] == 2


def test_degradation_rolling_robustness_and_promotion() -> None:
    timestamps = pd.date_range("2024-01-01", periods=60, freq="h")
    dataset = pd.DataFrame(
        {
            "timestamp": timestamps,
            "symbol": ["BTCUSDT"] * len(timestamps),
            "close": [100 + index for index in range(len(timestamps))],
            "pct_return": [0.01 if index % 4 else -0.008 for index in range(len(timestamps))],
        }
    )
    strategies = pd.DataFrame([{"strategy_id": "strategy_001"}])
    rolling = RollingEvaluator(window=12, step=6).evaluate(dataset, strategies)
    robustness = RobustnessMonitor().evaluate(rolling)
    health = robustness.assign(
        strategy_id="strategy_001",
        status="candidate",
        baseline_sharpe=1.2,
        recent_sharpe=0.6,
        baseline_win_rate=0.7,
        recent_win_rate=0.5,
        recent_drawdown=0.22,
        regime_shift=True,
    )
    degradation = DegradationDetector().detect_from_frame(health)
    decisions = PromotionEngine().evaluate(health.merge(degradation, on="strategy_id", how="left"))

    assert not rolling.empty
    assert not robustness.empty
    assert str(degradation.iloc[0]["degradation_level"]) in {"medium", "high"}
    assert str(decisions.iloc[0]["new_status"]) in {"deprecated", "paper_trading", "production_ready", "candidate"}


def test_regime_tracker_and_decision_log() -> None:
    base_dir = _base_dir()
    regimes = pd.DataFrame(
        [
            {"strategy_id": "unused", "symbol": "BTCUSDT", "regime_label": "bullish", "regime_confidence": 0.8},
            {"strategy_id": "unused", "symbol": "ETHUSDT", "regime_label": "sideways", "regime_confidence": 0.55},
        ]
    )
    strategies = pd.DataFrame([{"strategy_id": "strategy_001"}])
    performance = RegimePerformanceTracker().evaluate(regimes, strategies)
    log = DecisionLog(output_dir=str(base_dir / "governance"))
    record = log.record(
        strategy_id="strategy_001",
        previous_status="candidate",
        new_status="paper_trading",
        reason="promotion_thresholds_met",
        metrics_snapshot={"robustness_score": 25.0},
    )
    loaded = log.load()

    assert not performance.empty
    assert record["strategy_id"] == "strategy_001"
    assert len(loaded) == 1
