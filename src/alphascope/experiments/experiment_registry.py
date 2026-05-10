from __future__ import annotations


class ExperimentRegistry:
    def strategy_templates(self) -> list[dict[str, object]]:
        return [
            {"name": "oversold_reversal", "target_horizon": 4, "return_threshold": 0.015},
            {"name": "breakout_followthrough", "target_horizon": 6, "return_threshold": 0.02},
            {"name": "trend_confirmation", "target_horizon": 8, "return_threshold": 0.025},
        ]

    def target_definitions(self) -> list[dict[str, object]]:
        return [
            {"future_horizon": 4, "return_threshold": 0.015},
            {"future_horizon": 6, "return_threshold": 0.02},
        ]
