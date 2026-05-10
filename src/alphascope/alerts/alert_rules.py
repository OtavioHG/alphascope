"""Rules for deciding when operational alerts should fire."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass(slots=True)
class AlertRuleDecision:
    rule_name: str
    triggered: bool
    payload: dict[str, Any]


class AlertRuleEngine:
    """Evaluate runtime and ranking state transitions for alert dispatching."""

    def new_top_ranking(
        self,
        ranking: pd.DataFrame,
        *,
        previous_symbol: str | None,
        previous_score: float | None,
        min_score_delta: float = 0.0,
    ) -> AlertRuleDecision:
        if ranking.empty:
            return AlertRuleDecision("new_top_ranking", False, {})

        if "rank" in ranking.columns:
            top = ranking.sort_values("rank").iloc[0]
        else:
            score_column = "score" if "score" in ranking.columns else "final_score"
            top = ranking.sort_values(score_column, ascending=False).iloc[0]

        score = float(top.get("score", top.get("final_score", 0.0)) or 0.0)
        symbol = str(top.get("symbol", "") or "")
        should_trigger = (
            bool(symbol)
            and (
                previous_symbol != symbol
                or previous_score is None
                or abs(score - previous_score) >= min_score_delta
            )
        )
        return AlertRuleDecision(
            "new_top_ranking",
            should_trigger,
            {
                "symbol": symbol,
                "score": score,
                "rank": int(top.get("rank", 1) or 1),
            },
        )

    def heartbeat_lost(self, runtime_status: dict[str, Any], *, already_alerted: bool = False) -> AlertRuleDecision:
        recovery = runtime_status.get("recovery", {})
        issues = recovery.get("issues", [])
        issue = next(
            (
                item
                for item in issues
                if str(item.get("code")) in {"stale_heartbeat", "invalid_heartbeat"}
            ),
            None,
        )
        if issue is None or already_alerted:
            return AlertRuleDecision("heartbeat_lost", False, {})

        heartbeat = runtime_status.get("heartbeat", {})
        daemon = runtime_status.get("daemon", {})
        return AlertRuleDecision(
            "heartbeat_lost",
            True,
            {
                "issue_code": issue.get("code"),
                "heartbeat_timestamp": heartbeat.get("timestamp"),
                "daemon_status": daemon.get("status"),
            },
        )

    def daemon_stopped(
        self,
        runtime_status: dict[str, Any],
        *,
        previous_status: str | None,
    ) -> AlertRuleDecision:
        daemon = runtime_status.get("daemon", {})
        current_status = str(daemon.get("status") or "")
        triggered = previous_status not in {None, "", "stopped"} and current_status == "stopped"
        return AlertRuleDecision(
            "daemon_stopped",
            triggered,
            {
                "status": current_status or "stopped",
                "cycle_count": daemon.get("cycle_count", 0),
                "consecutive_errors": daemon.get("consecutive_errors", 0),
            },
        )
