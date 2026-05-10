from __future__ import annotations


class ApprovalRules:
    def __init__(
        self,
        min_robustness: float = 20.0,
        min_rolling_sharpe: float = 0.2,
        max_drawdown: float = 0.18,
    ):
        self.min_robustness = min_robustness
        self.min_rolling_sharpe = min_rolling_sharpe
        self.max_drawdown = max_drawdown

    def evaluate(
        self,
        robustness_score: float,
        rolling_sharpe: float,
        rolling_drawdown: float,
        degradation_level: str,
        current_status: str,
    ) -> dict[str, object]:
        if degradation_level in {"high", "medium"} or rolling_drawdown > self.max_drawdown:
            return {"new_status": "deprecated", "reason": "degradation_or_drawdown"}
        if (
            robustness_score >= self.min_robustness
            and rolling_sharpe >= self.min_rolling_sharpe
            and current_status in {"candidate", "paper_trading"}
        ):
            return {
                "new_status": "paper_trading" if current_status == "candidate" else "production_ready",
                "reason": "promotion_thresholds_met",
            }
        return {"new_status": current_status, "reason": "no_change"}
