"""Scoring helpers for multi-agent consensus."""

from __future__ import annotations

from typing import Iterable

from alphascope.agents.schemas import AgentOutput


class ScoringEngine:
    BASE_WEIGHTS = {
        "nemotron": 0.40,
        "gpt_oss": 0.30,
        "minimax": 0.20,
        "trinity": 0.10,
    }

    SIGNAL_TO_SCORE = {
        "buy": 1.0,
        "hold": 0.5,
        "sell": 0.0,
    }

    @classmethod
    def normalize_confidence(cls, value: float) -> float:
        return max(0.0, min(1.0, float(value)))

    @classmethod
    def signal_score(cls, signal: str, confidence: float) -> float:
        base = cls.SIGNAL_TO_SCORE.get(str(signal).lower(), 0.5)
        confidence = cls.normalize_confidence(confidence)
        return max(0.0, min(1.0, (base * 0.7) + (confidence * 0.3)))

    @classmethod
    def aggregate_output_scores(cls, outputs: Iterable[AgentOutput]) -> float:
        values = [cls.signal_score(output.signal, output.confidence) for output in outputs]
        if not values:
            return 0.5
        return float(sum(values) / len(values))

    @classmethod
    def rebalance_weights(cls, dynamic_metrics: dict[str, float] | None = None) -> dict[str, float]:
        metrics = dynamic_metrics or {}
        weighted = {}
        total = 0.0
        for key, default in cls.BASE_WEIGHTS.items():
            multiplier = max(0.25, min(1.75, float(metrics.get(key, 1.0))))
            value = default * multiplier
            weighted[key] = value
            total += value
        if total <= 0:
            return dict(cls.BASE_WEIGHTS)
        return {key: value / total for key, value in weighted.items()}
