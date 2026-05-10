from __future__ import annotations

import itertools
from pathlib import Path

import pandas as pd

from alphascope.experiments.experiment_registry import ExperimentRegistry


class ExperimentManager:
    def __init__(self, output_dir: str = "data/processed/experiments"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.registry = ExperimentRegistry()

    def run_batch(
        self,
        selected_features: list[str],
        regimes: pd.DataFrame,
        mined_signals: pd.DataFrame,
    ) -> pd.DataFrame:
        templates = self.registry.strategy_templates()
        experiments: list[dict[str, object]] = []
        subset_sizes = sorted({max(1, min(3, len(selected_features))), max(1, min(5, len(selected_features)))})
        for index, (template, feature_subset_size) in enumerate(itertools.product(templates, subset_sizes), start=1):
            subset = selected_features[:feature_subset_size]
            experiments.append(
                {
                    "experiment_id": f"exp_{index:03d}",
                    "strategy_id": template["name"],
                    "feature_set": subset,
                    "target_definition": {
                        "future_horizon": template["target_horizon"],
                        "return_threshold": template["return_threshold"],
                    },
                    "train_period": "historical",
                    "test_period": "forward_slice",
                    "metrics": {
                        "signal_count": int(len(mined_signals)),
                        "regime_coverage": int(regimes["regime_label"].nunique()) if not regimes.empty else 0,
                    },
                    "promotion_status": "research_only",
                }
            )
        result = pd.DataFrame(experiments)
        result.to_json(self.output_dir / "experiment_manager_batch.json", orient="records", indent=2)
        return result
