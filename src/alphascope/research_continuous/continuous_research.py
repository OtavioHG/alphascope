from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from alphascope.evolution.adaptation_engine import AdaptationEngine
from alphascope.evolution.degradation_detector import DegradationDetector
from alphascope.evolution.promotion_engine import PromotionEngine
from alphascope.evolution.retraining_manager import RetrainingManager
from alphascope.evolution.strategy_lifecycle import StrategyLifecycle
from alphascope.evolution.strategy_registry import StrategyRegistry
from alphascope.evolution.strategy_versioning import StrategyVersioning
from alphascope.governance.decision_log import DecisionLog
from alphascope.governance.strategy_policy import StrategyPolicy
from alphascope.research.research_pipeline import ResearchPipeline
from alphascope.research_continuous.regime_performance_tracker import RegimePerformanceTracker
from alphascope.research_continuous.robustness_monitor import RobustnessMonitor
from alphascope.research_continuous.rolling_evaluator import RollingEvaluator
from alphascope.reports.degradation_reports import DegradationReportBuilder
from alphascope.reports.lifecycle_reports import LifecycleReportBuilder
from alphascope.reports.promotion_reports import PromotionReportBuilder


class ContinuousResearchPipeline:
    def __init__(
        self,
        dataset_path: str = "data/processed/dataset.csv",
        evolution_dir: str = "data/processed/evolution",
        lifecycle_dir: str = "data/processed/lifecycle",
        governance_dir: str = "data/processed/governance",
        reports_dir: str = "data/processed/reports",
    ):
        self.dataset_path = dataset_path
        self.evolution_dir = Path(evolution_dir)
        self.lifecycle_dir = Path(lifecycle_dir)
        self.governance_dir = Path(governance_dir)
        self.reports_dir = Path(reports_dir)
        for directory in [self.evolution_dir, self.lifecycle_dir, self.governance_dir, self.reports_dir]:
            directory.mkdir(parents=True, exist_ok=True)

        self.research = ResearchPipeline(dataset_path=dataset_path)
        self.registry = StrategyRegistry(output_dir=str(self.lifecycle_dir))
        self.versioning = StrategyVersioning(output_dir=str(self.lifecycle_dir))
        self.lifecycle = StrategyLifecycle(registry=self.registry, output_dir=str(self.lifecycle_dir))
        self.degradation = DegradationDetector()
        self.retraining = RetrainingManager(output_dir=str(self.evolution_dir))
        self.adaptation = AdaptationEngine(output_dir=str(self.evolution_dir))
        self.rolling = RollingEvaluator()
        self.robustness = RobustnessMonitor()
        self.regime_tracker = RegimePerformanceTracker()
        self.promotion = PromotionEngine()
        self.policy = StrategyPolicy()
        self.decision_log = DecisionLog(output_dir=str(self.governance_dir))
        self.lifecycle_report = LifecycleReportBuilder(output_dir=str(self.reports_dir))
        self.degradation_report = DegradationReportBuilder(output_dir=str(self.reports_dir))
        self.promotion_report = PromotionReportBuilder(output_dir=str(self.reports_dir))

    def bootstrap_registry(self, strategies: pd.DataFrame) -> pd.DataFrame:
        registry = self.registry.load()
        for _, row in strategies.iterrows():
            if registry.empty or str(row["strategy_id"]) not in set(registry["strategy_id"]):
                self.registry.register(
                    {
                        "strategy_id": row["strategy_id"],
                        "strategy_name": row["strategy_id"],
                        "parent_strategy_id": None,
                        "version": 1,
                        "status": row.get("promotion_status", "research_only"),
                        "creation_source": "phase8_research",
                        "current_stage": row.get("promotion_status", "research_only"),
                        "features_used": [],
                        "target_definition": row.get("target_definition", {}),
                        "thresholds": {"buy": 0.75, "sell": 0.35},
                        "regime_filters": [],
                        "risk_rules": {"max_drawdown": 0.2},
                        "performance_summary": row.get("evaluation_metrics", {}),
                    }
                )
        return self.registry.load()

    def evaluate_strategy_health(self) -> dict[str, pd.DataFrame]:
        research_result = self.research.run()
        registry = self.bootstrap_registry(research_result["strategies"])
        rolling_metrics = self.rolling.evaluate(research_result["dataset"], research_result["strategies"])
        robustness = self.robustness.evaluate(rolling_metrics, research_result["ranking"])
        regime_performance = self.regime_tracker.evaluate(research_result["regimes"], research_result["strategies"])

        health = registry[["strategy_id", "status", "version"]].copy()
        health = health.merge(robustness, on="strategy_id", how="left")
        if not regime_performance.empty:
            health = health.merge(
                regime_performance[["strategy_id", "best_regime", "worst_regime", "regime_dependence_score"]],
                on="strategy_id",
                how="left",
            )
        health["baseline_sharpe"] = health["rolling_sharpe"].fillna(0.0) + 0.2
        health["recent_sharpe"] = health["rolling_sharpe"].fillna(0.0)
        health["baseline_win_rate"] = health["rolling_win_rate"].fillna(0.0) + 0.05
        health["recent_win_rate"] = health["rolling_win_rate"].fillna(0.0)
        health["recent_drawdown"] = health["rolling_drawdown"].fillna(0.0)
        health["regime_shift"] = health["regime_dependence_score"].fillna(0.0) > 0.2
        degradation = self.degradation.detect_from_frame(health)
        health = health.merge(degradation, on="strategy_id", how="left")
        health.to_csv(self.evolution_dir / "strategy_health.csv", index=False)
        rolling_metrics.to_csv(self.evolution_dir / "rolling_metrics.csv", index=False)
        robustness.to_csv(self.evolution_dir / "robustness_scores.csv", index=False)
        regime_performance.to_json(self.evolution_dir / "regime_performance.json", orient="records", indent=2)
        return {
            "health": health,
            "rolling_metrics": rolling_metrics,
            "robustness": robustness,
            "regime_performance": regime_performance,
            "research": research_result["ranking"],
        }

    def run(self) -> dict[str, Any]:
        evaluated = self.evaluate_strategy_health()
        health = evaluated["health"]
        adaptations = self.adaptation.generate_candidates(self.registry.load(), health)
        decisions = self.promotion.evaluate(health)

        for _, row in adaptations.iterrows():
            self.versioning.create_version(
                strategy_id=str(row["strategy_id"]),
                parent_strategy_id=str(row["parent_strategy_id"]),
                version=int(row["candidate_strategy_versions"]),
                changes={
                    "threshold_adjustment": row["threshold_adjustment"],
                    "target_horizon": row["target_horizon"],
                    "adaptation_reason": row["adaptation_reason"],
                },
            )
            self.registry.register(
                {
                    "strategy_id": row["strategy_id"],
                    "strategy_name": row["strategy_id"],
                    "parent_strategy_id": row["parent_strategy_id"],
                    "version": int(row["candidate_strategy_versions"]),
                    "status": row["promotion_status"],
                    "creation_source": "adaptation_engine",
                    "promoted_from": row["parent_strategy_id"],
                    "current_stage": row["promotion_status"],
                    "features_used": [],
                    "target_definition": {"future_horizon": int(row["target_horizon"])},
                    "thresholds": row["threshold_adjustment"],
                    "regime_filters": [],
                    "risk_rules": {"max_drawdown": 0.2},
                    "performance_summary": {"expected_improvement": float(row["expected_improvement"])},
                }
            )

        for _, row in decisions.iterrows():
            strategy_id = str(row["strategy_id"])
            current = self.registry.load().loc[lambda frame: frame["strategy_id"] == strategy_id]
            if current.empty:
                continue
            previous_status = str(current.iloc[-1]["status"])
            new_status = str(row["new_status"])
            if previous_status != new_status and self.policy.allows_transition(previous_status, new_status):
                self.lifecycle.transition(strategy_id, new_status, str(row["reason"]))
            self.decision_log.record(
                strategy_id=strategy_id,
                previous_status=previous_status,
                new_status=new_status,
                reason=str(row["reason"]),
                metrics_snapshot=row.to_dict(),
            )

        retraining_decisions = []
        for _, row in health.iterrows():
            retraining_decisions.append(
                {
                    "strategy_id": row["strategy_id"],
                    **self.retraining.evaluate_trigger(
                        performance_drift=float(row.get("degradation_score", 0.0)),
                        regime_shift=bool(row.get("regime_shift", False)),
                        elapsed_windows=int(row.get("window_count", 0)),
                    ),
                }
            )
        retraining_frame = pd.DataFrame(retraining_decisions)
        retraining_frame.to_csv(self.evolution_dir / "retraining_decisions.csv", index=False)
        decisions.to_csv(self.governance_dir / "promotion_decisions.csv", index=False)
        self.lifecycle_report.build(self.registry.load(), self.lifecycle.load_transitions())
        self.degradation_report.build(health)
        self.promotion_report.build(decisions)
        summary = {
            "health_rows": int(len(health)),
            "adaptation_rows": int(len(adaptations)),
            "decision_rows": int(len(decisions)),
            "retraining_rows": int(len(retraining_frame)),
        }
        (self.reports_dir / "continuous_research_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        return {
            "health": health,
            "adaptations": adaptations,
            "decisions": decisions,
            "retraining": retraining_frame,
            "summary": summary,
        }
