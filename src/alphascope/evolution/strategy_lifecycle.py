from __future__ import annotations

from pathlib import Path

import pandas as pd

from alphascope.evolution.strategy_registry import ALLOWED_STATUSES, StrategyRegistry


ALLOWED_TRANSITIONS = {
    "research_only": {"candidate", "archived"},
    "candidate": {"paper_trading", "deprecated", "archived", "research_only"},
    "paper_trading": {"production_ready", "deprecated", "candidate"},
    "production_ready": {"deprecated", "paper_trading"},
    "deprecated": {"archived", "candidate"},
    "archived": set(),
}


class StrategyLifecycle:
    def __init__(self, registry: StrategyRegistry | None = None, output_dir: str = "data/processed/lifecycle"):
        self.registry = registry or StrategyRegistry(output_dir=output_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.transitions_path = self.output_dir / "lifecycle_transitions.csv"

    def transition(self, strategy_id: str, new_status: str, reason: str) -> pd.DataFrame:
        if new_status not in ALLOWED_STATUSES:
            raise ValueError("Invalid lifecycle status")
        registry = self.registry.load()
        row = registry.loc[registry["strategy_id"] == strategy_id]
        if row.empty:
            raise KeyError(f"Strategy not found: {strategy_id}")
        previous_status = str(row.iloc[-1]["status"])
        if new_status not in ALLOWED_TRANSITIONS.get(previous_status, set()):
            raise ValueError(f"Transition {previous_status} -> {new_status} not allowed")
        self.registry.update_status(strategy_id, new_status)
        transitions = self.load_transitions()
        transitions = pd.concat(
            [
                transitions,
                pd.DataFrame(
                    [
                        {
                            "strategy_id": strategy_id,
                            "previous_status": previous_status,
                            "new_status": new_status,
                            "reason": reason,
                        }
                    ]
                ),
            ],
            ignore_index=True,
        )
        transitions.to_csv(self.transitions_path, index=False)
        return transitions

    def load_transitions(self) -> pd.DataFrame:
        if not self.transitions_path.exists():
            return pd.DataFrame(columns=["strategy_id", "previous_status", "new_status", "reason"])
        return pd.read_csv(self.transitions_path)
