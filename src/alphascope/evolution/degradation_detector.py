from __future__ import annotations

import pandas as pd


class DegradationDetector:
    def __init__(self, sharpe_drop_threshold: float = 0.25, drawdown_limit: float = 0.20, win_rate_drop_threshold: float = 0.10):
        self.sharpe_drop_threshold = sharpe_drop_threshold
        self.drawdown_limit = drawdown_limit
        self.win_rate_drop_threshold = win_rate_drop_threshold

    def detect(self, baseline: dict[str, float], recent: dict[str, float], regime_shift: bool = False) -> dict[str, object]:
        baseline_sharpe = float(baseline.get("sharpe", 0.0))
        recent_sharpe = float(recent.get("sharpe", 0.0))
        baseline_win_rate = float(baseline.get("win_rate", 0.0))
        recent_win_rate = float(recent.get("win_rate", 0.0))
        recent_drawdown = float(recent.get("max_drawdown", 0.0))

        reasons: list[str] = []
        score = 0.0
        if baseline_sharpe > 0:
            sharpe_drop = max(0.0, (baseline_sharpe - recent_sharpe) / baseline_sharpe)
            if sharpe_drop >= self.sharpe_drop_threshold:
                reasons.append("sharpe_drop")
                score += sharpe_drop
        if recent_drawdown >= self.drawdown_limit:
            reasons.append("drawdown_exceeded")
            score += recent_drawdown
        if baseline_win_rate > 0 and (baseline_win_rate - recent_win_rate) >= self.win_rate_drop_threshold:
            reasons.append("win_rate_drop")
            score += baseline_win_rate - recent_win_rate
        if regime_shift:
            reasons.append("regime_shift")
            score += 0.15

        level = "none"
        if score >= 0.6:
            level = "high"
        elif score >= 0.25:
            level = "medium"
        elif score > 0:
            level = "low"

        return {
            "degradation_score": round(score, 4),
            "degradation_reason": ", ".join(reasons) if reasons else "stable",
            "degradation_level": level,
        }

    def detect_from_frame(self, frame: pd.DataFrame) -> pd.DataFrame:
        if frame.empty:
            return pd.DataFrame()
        results = []
        for _, row in frame.iterrows():
            results.append(
                {
                    "strategy_id": row["strategy_id"],
                    **self.detect(
                        baseline={
                            "sharpe": row.get("baseline_sharpe", 0.0),
                            "win_rate": row.get("baseline_win_rate", 0.0),
                        },
                        recent={
                            "sharpe": row.get("recent_sharpe", 0.0),
                            "win_rate": row.get("recent_win_rate", 0.0),
                            "max_drawdown": row.get("recent_drawdown", 0.0),
                        },
                        regime_shift=bool(row.get("regime_shift", False)),
                    ),
                }
            )
        return pd.DataFrame(results)
