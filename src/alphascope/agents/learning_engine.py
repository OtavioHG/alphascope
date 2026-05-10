"""Learning and retraining for AlphaScope multi-agent models."""

from __future__ import annotations

import importlib.util
import json
import pickle
from pathlib import Path
from typing import Any

import pandas as pd

from alphascope.agents.repository import MultiAgentRepository
from alphascope.config.settings import settings


class MultiAgentLearningEngine:
    MODEL_TARGETS = {
        "local_market_model": ["market_score", "news_score", "risk_score", "memory_score", "final_score"],
        "local_risk_model": ["risk_score", "final_score"],
        "local_news_model": ["news_score", "final_score"],
        "local_consensus_model": ["market_score", "news_score", "risk_score", "memory_score", "final_score"],
        "local_execution_model": ["final_score", "risk_score"],
    }

    def __init__(self, repository: MultiAgentRepository | None = None) -> None:
        self.repository = repository or MultiAgentRepository()
        from alphascope.continuous_learning.manager import ContinuousLearningManager

        self.continuous_learning = ContinuousLearningManager(repository=self.repository.storage)

    def export_training_frame(self, *, limit: int = 1000) -> pd.DataFrame:
        consensus_rows = pd.DataFrame(self.repository.get_recent_consensus(limit=limit))
        decision_rows = pd.DataFrame(self.repository.get_recent_agent_decisions(limit=limit * 4))
        if consensus_rows.empty:
            return pd.DataFrame()
        score_rows: list[dict[str, Any]] = []
        for row in consensus_rows.to_dict(orient="records"):
            component_scores = row.get("component_scores") or {}
            score_rows.append(
                {
                    "symbol": row.get("symbol"),
                    "decision": row.get("decision"),
                    "final_score": float(row.get("final_score", 0.0) or 0.0),
                    "realized_pnl": float(row.get("realized_pnl", 0.0) or 0.0),
                    "market_score": float(component_scores.get("nemotron", 0.0) or 0.0),
                    "news_score": float(component_scores.get("gpt_oss", 0.0) or 0.0),
                    "risk_score": float(component_scores.get("minimax", 0.0) or 0.0),
                    "memory_score": float(component_scores.get("trinity", 0.0) or 0.0),
                    "target": 1 if float(row.get("realized_pnl", 0.0) or 0.0) > 0 else 0,
                }
            )
        frame = pd.DataFrame(score_rows)
        if not decision_rows.empty and "agent" in decision_rows.columns:
            summary = decision_rows.groupby("agent")["confidence"].mean().to_dict()
            frame["market_agent_confidence"] = float(summary.get("market_intelligence", 0.0) or 0.0)
            frame["news_agent_confidence"] = float(summary.get("news_sentiment", 0.0) or 0.0)
            frame["risk_agent_confidence"] = float(summary.get("risk_manager", 0.0) or 0.0)
            frame["memory_agent_confidence"] = float(summary.get("memory_engine", 0.0) or 0.0)
        return frame

    def train_models(self, *, limit: int = 1000) -> dict[str, Any]:
        frame = self.export_training_frame(limit=limit)
        result: dict[str, Any] = {
            "training_rows": int(len(frame)),
            "available_trainers": self.available_trainers(),
            "trained_models": [],
            "skipped_models": [],
        }
        models_dir = settings.model_dir
        models_dir.mkdir(parents=True, exist_ok=True)
        if frame.empty or len(frame) < 10:
            result["reason"] = "insufficient_training_rows"
            return result

        trainer_name, trainer_builder = self._select_trainer()
        if trainer_builder is None:
            result["reason"] = "no_supported_ml_library"
            return result

        for model_name, feature_columns in self.MODEL_TARGETS.items():
            usable_columns = [column for column in feature_columns if column in frame.columns]
            if not usable_columns:
                result["skipped_models"].append({"model": model_name, "reason": "missing_feature_columns"})
                continue
            dataset = frame.loc[:, usable_columns + ["target"]].dropna().copy()
            if len(dataset) < 10 or dataset["target"].nunique() < 2:
                result["skipped_models"].append({"model": model_name, "reason": "insufficient_target_variation"})
                continue
            estimator = trainer_builder()
            estimator.fit(dataset[usable_columns], dataset["target"])
            artifact_path = models_dir / f"{model_name}.pkl"
            metadata_path = models_dir / f"{model_name}.json"
            with artifact_path.open("wb") as handle:
                pickle.dump(estimator, handle)
            metadata = {
                "model_name": model_name,
                "trainer": trainer_name,
                "feature_columns": usable_columns,
                "rows": int(len(dataset)),
                "target_positive_rate": float(dataset["target"].mean()),
            }
            metadata_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
            result["trained_models"].append({"model": model_name, "trainer": trainer_name, "artifact_path": str(artifact_path)})
        return result

    def maybe_retrain(self, *, symbols: list[str], interval: str, cycle_count: int) -> dict[str, Any]:
        lifecycle_result = self.continuous_learning.maybe_run_retraining(symbols=symbols, interval=interval, cycle_count=cycle_count)
        local_result = self.train_models(limit=max(250, cycle_count * 5))
        return {
            "lifecycle": lifecycle_result,
            "local_training": local_result,
        }

    @staticmethod
    def available_trainers() -> dict[str, bool]:
        return {
            "sklearn": importlib.util.find_spec("sklearn") is not None,
            "xgboost": importlib.util.find_spec("xgboost") is not None,
            "lightgbm": importlib.util.find_spec("lightgbm") is not None,
            "catboost": importlib.util.find_spec("catboost") is not None,
            "torch": importlib.util.find_spec("torch") is not None,
            "transformers": importlib.util.find_spec("transformers") is not None,
            "sentence_transformers": importlib.util.find_spec("sentence_transformers") is not None,
        }

    def _select_trainer(self):
        if importlib.util.find_spec("xgboost") is not None:
            from xgboost import XGBClassifier  # type: ignore

            return "xgboost", lambda: XGBClassifier(n_estimators=50, max_depth=3, eval_metric="logloss")
        if importlib.util.find_spec("lightgbm") is not None:
            from lightgbm import LGBMClassifier  # type: ignore

            return "lightgbm", lambda: LGBMClassifier(n_estimators=50)
        if importlib.util.find_spec("catboost") is not None:
            from catboost import CatBoostClassifier  # type: ignore

            return "catboost", lambda: CatBoostClassifier(verbose=False)
        if importlib.util.find_spec("sklearn") is not None:
            from sklearn.ensemble import GradientBoostingClassifier

            return "sklearn_gradient_boosting", lambda: GradientBoostingClassifier(random_state=42)
        return None, None
