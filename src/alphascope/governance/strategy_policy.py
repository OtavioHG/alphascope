from __future__ import annotations


class StrategyPolicy:
    def allows_transition(self, previous_status: str, new_status: str) -> bool:
        transitions = {
            "research_only": {"candidate", "archived"},
            "candidate": {"paper_trading", "deprecated", "archived", "research_only"},
            "paper_trading": {"production_ready", "deprecated", "candidate"},
            "production_ready": {"deprecated", "paper_trading"},
            "deprecated": {"archived", "candidate"},
            "archived": set(),
        }
        return new_status in transitions.get(previous_status, set())
