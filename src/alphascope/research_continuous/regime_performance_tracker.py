from __future__ import annotations

import pandas as pd


class RegimePerformanceTracker:
    def evaluate(self, regimes: pd.DataFrame, strategies: pd.DataFrame) -> pd.DataFrame:
        if regimes.empty or strategies.empty:
            return pd.DataFrame()
        regime_summary = (
            regimes.groupby("regime_label")
            .agg(
                regime_confidence=("regime_confidence", "mean"),
                observations=("symbol", "count"),
            )
            .reset_index()
        )
        rows: list[dict[str, object]] = []
        for _, strategy in strategies.iterrows():
            best_row = regime_summary.sort_values("regime_confidence", ascending=False).iloc[0]
            worst_row = regime_summary.sort_values("regime_confidence", ascending=True).iloc[0]
            rows.append(
                {
                    "strategy_id": strategy["strategy_id"],
                    "performance_by_regime": regime_summary.to_dict(orient="records"),
                    "best_regime": str(best_row["regime_label"]),
                    "worst_regime": str(worst_row["regime_label"]),
                    "regime_dependence_score": float(best_row["regime_confidence"] - worst_row["regime_confidence"]),
                }
            )
        return pd.DataFrame(rows)
