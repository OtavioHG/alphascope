from __future__ import annotations

import pandas as pd

from alphascope.governance.approval_rules import ApprovalRules


class PromotionEngine:
    def __init__(self, rules: ApprovalRules | None = None):
        self.rules = rules or ApprovalRules()

    def evaluate(self, health: pd.DataFrame) -> pd.DataFrame:
        if health.empty:
            return pd.DataFrame()
        decisions: list[dict[str, object]] = []
        for _, row in health.iterrows():
            decision = self.rules.evaluate(
                robustness_score=float(row.get("robustness_score", 0.0)),
                rolling_sharpe=float(row.get("rolling_sharpe", 0.0)),
                rolling_drawdown=float(row.get("rolling_drawdown", 0.0)),
                degradation_level=str(row.get("degradation_level", "none")),
                current_status=str(row.get("status", "research_only")),
            )
            decisions.append({"strategy_id": row["strategy_id"], **decision})
        return pd.DataFrame(decisions)
