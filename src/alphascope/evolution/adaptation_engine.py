from __future__ import annotations

from pathlib import Path

import pandas as pd


class AdaptationEngine:
    def __init__(self, output_dir: str = "data/processed/evolution"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_candidates(self, registry: pd.DataFrame, health: pd.DataFrame) -> pd.DataFrame:
        if registry.empty:
            return pd.DataFrame()
        health_map = health.set_index("strategy_id").to_dict(orient="index") if not health.empty else {}
        candidates: list[dict[str, object]] = []
        for _, row in registry.iterrows():
            strategy_id = str(row["strategy_id"])
            health_row = health_map.get(strategy_id, {})
            if float(health_row.get("degradation_score", 0.0)) < 0.2:
                continue
            version = int(row.get("version", 1)) + 1
            candidates.append(
                {
                    "strategy_id": f"{strategy_id}_v{version}",
                    "parent_strategy_id": strategy_id,
                    "candidate_strategy_versions": version,
                    "adaptation_reason": health_row.get("degradation_reason", "performance_review"),
                    "expected_improvement": round(0.05 + float(health_row.get("degradation_score", 0.0)) * 0.2, 4),
                    "threshold_adjustment": {"buy": 0.73, "sell": 0.37},
                    "target_horizon": 6 if "trend" in strategy_id else 4,
                    "promotion_status": "candidate",
                }
            )
        frame = pd.DataFrame(candidates)
        frame.to_json(self.output_dir / "adaptation_candidates.json", orient="records", indent=2)
        return frame
