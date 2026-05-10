from __future__ import annotations

import pandas as pd


class AlphaRanker:
    def rank(self, strategies: pd.DataFrame, mined_signals: pd.DataFrame | None = None) -> pd.DataFrame:
        if strategies.empty:
            return pd.DataFrame()

        frame = strategies.copy()
        if mined_signals is not None and not mined_signals.empty and "signal_definition" in frame.columns:
            keep = [
                column
                for column in [
                    "signal_definition",
                    "asset_count",
                    "sample_count",
                    "win_rate",
                    "sharpe",
                    "max_drawdown",
                    "stability_score",
                ]
                if column in mined_signals.columns
            ]
            if keep:
                frame = frame.merge(mined_signals[keep], on="signal_definition", how="left")

        metrics = frame["evaluation_metrics"].apply(lambda value: value if isinstance(value, dict) else {})
        if "sample_count" not in frame.columns:
            frame["sample_count"] = metrics.apply(lambda item: int(item.get("sample_count", 0)))
        if "win_rate" not in frame.columns:
            frame["win_rate"] = metrics.apply(lambda item: float(item.get("win_rate", 0.0)))
        if "sharpe" not in frame.columns:
            frame["sharpe"] = metrics.apply(lambda item: float(item.get("sharpe", 0.0)))
        if "max_drawdown" not in frame.columns:
            frame["max_drawdown"] = metrics.apply(lambda item: float(item.get("max_drawdown", 0.0)))
        if "stability_score" not in frame.columns:
            frame["stability_score"] = metrics.apply(lambda item: float(item.get("stability_score", 0.0)))
        if "asset_count" not in frame.columns:
            frame["asset_count"] = 1

        frame["alpha_discovery_score"] = (
            frame["sharpe"].clip(lower=0.0) * 30.0
            + frame["win_rate"].clip(lower=0.0) * 25.0
            + frame["stability_score"].clip(lower=0.0) * 100.0
            + frame["asset_count"].fillna(1).clip(lower=1) * 4.0
            - frame["max_drawdown"].clip(lower=0.0) * 40.0
            - (1.0 / frame["sample_count"].fillna(1).clip(lower=1)) * 20.0
        )
        return frame.sort_values("alpha_discovery_score", ascending=False).reset_index(drop=True)
