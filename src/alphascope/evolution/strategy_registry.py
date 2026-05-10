from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ALLOWED_STATUSES = {
    "research_only",
    "candidate",
    "paper_trading",
    "production_ready",
    "deprecated",
    "archived",
}


class StrategyRegistry:
    def __init__(self, output_dir: str = "data/processed/lifecycle"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.registry_path = self.output_dir / "strategy_registry.csv"

    def load(self) -> pd.DataFrame:
        if not self.registry_path.exists():
            return pd.DataFrame(
                columns=[
                    "strategy_id",
                    "strategy_name",
                    "parent_strategy_id",
                    "version",
                    "status",
                    "creation_source",
                    "promoted_from",
                    "current_stage",
                    "features_used",
                    "target_definition",
                    "thresholds",
                    "regime_filters",
                    "risk_rules",
                    "performance_summary",
                ]
            )
        frame = pd.read_csv(self.registry_path)
        return frame

    def register(self, strategy: dict[str, object]) -> pd.DataFrame:
        if str(strategy.get("status", "research_only")) not in ALLOWED_STATUSES:
            raise ValueError("Invalid strategy status")
        registry = self.load()
        strategy_id = str(strategy["strategy_id"])
        record = {
            "strategy_id": strategy_id,
            "strategy_name": strategy.get("strategy_name", strategy_id),
            "parent_strategy_id": strategy.get("parent_strategy_id"),
            "version": int(strategy.get("version", 1)),
            "status": strategy.get("status", "research_only"),
            "creation_source": strategy.get("creation_source", "phase8_research"),
            "promoted_from": strategy.get("promoted_from"),
            "current_stage": strategy.get("current_stage", strategy.get("status", "research_only")),
            "features_used": json.dumps(strategy.get("features_used", []), default=str),
            "target_definition": json.dumps(strategy.get("target_definition", {}), default=str),
            "thresholds": json.dumps(strategy.get("thresholds", {}), default=str),
            "regime_filters": json.dumps(strategy.get("regime_filters", []), default=str),
            "risk_rules": json.dumps(strategy.get("risk_rules", {}), default=str),
            "performance_summary": json.dumps(strategy.get("performance_summary", {}), default=str),
        }
        registry = registry.loc[registry["strategy_id"] != strategy_id].copy()
        registry = pd.concat([registry, pd.DataFrame([record])], ignore_index=True)
        registry.to_csv(self.registry_path, index=False)
        return registry

    def update_status(self, strategy_id: str, status: str) -> pd.DataFrame:
        if status not in ALLOWED_STATUSES:
            raise ValueError("Invalid strategy status")
        registry = self.load()
        if registry.empty or strategy_id not in set(registry["strategy_id"]):
            raise KeyError(f"Strategy not found: {strategy_id}")
        registry.loc[registry["strategy_id"] == strategy_id, ["status", "current_stage"]] = status
        registry.to_csv(self.registry_path, index=False)
        return registry
