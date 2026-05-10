from __future__ import annotations

import pandas as pd


class RobustnessMonitor:
    def evaluate(self, rolling_metrics: pd.DataFrame, ranked_alpha: pd.DataFrame | None = None) -> pd.DataFrame:
        if rolling_metrics.empty:
            return pd.DataFrame()
        frame = rolling_metrics.copy()
        if ranked_alpha is not None and not ranked_alpha.empty:
            keep = [column for column in ["strategy_id", "asset_count", "alpha_discovery_score"] if column in ranked_alpha.columns]
            if keep:
                frame = frame.merge(ranked_alpha[keep], on="strategy_id", how="left")
        if "asset_count" not in frame.columns:
            frame["asset_count"] = 1
        frame["asset_count"] = frame["asset_count"].fillna(1)
        frame["robustness_score"] = (
            frame["rolling_sharpe"].clip(lower=0.0) * 25.0
            + frame["rolling_win_rate"].clip(lower=0.0) * 20.0
            + frame["rolling_profit_factor"].clip(lower=0.0) * 10.0
            + frame["asset_count"].clip(lower=1) * 3.0
            - frame["rolling_drawdown"].clip(lower=0.0) * 30.0
            - (1.0 / frame["window_count"].clip(lower=1)) * 10.0
        )
        frame["instability_flags"] = frame.apply(
            lambda row: ", ".join(
                flag
                for flag, active in {
                    "few_windows": int(row["window_count"]) < 3,
                    "high_drawdown": float(row["rolling_drawdown"]) > 0.15,
                    "low_asset_diversity": float(row["asset_count"]) <= 1,
                }.items()
                if active
            )
            or "stable",
            axis=1,
        )
        return frame[["strategy_id", "robustness_score", "instability_flags", "rolling_sharpe", "rolling_drawdown", "rolling_win_rate", "rolling_profit_factor", "window_count"]]
