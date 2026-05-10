"""Optimization package exports."""

from __future__ import annotations

try:
    from alphascope.optimization.tuner import StrategyTuner
except Exception:  # pragma: no cover - optional dependency such as optuna may be unavailable
    StrategyTuner = None

__all__ = ["StrategyTuner"]
