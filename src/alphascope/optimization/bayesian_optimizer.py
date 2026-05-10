from __future__ import annotations

import random
from typing import Callable

try:
    import optuna
except Exception:
    optuna = None


class BayesianOptimizer:
    def __init__(self, seed: int = 42):
        self.seed = seed
        random.seed(seed)

    def optimize(
        self,
        objective: Callable[[dict[str, float]], float],
        search_space: dict[str, tuple[float, float]],
        n_trials: int = 20,
    ) -> dict[str, object]:
        if optuna is not None:
            sampler = optuna.samplers.TPESampler(seed=self.seed)
            study = optuna.create_study(direction="maximize", sampler=sampler)

            def _objective(trial):
                params = {
                    name: trial.suggest_float(name, bounds[0], bounds[1])
                    for name, bounds in search_space.items()
                }
                return objective(params)

            study.optimize(_objective, n_trials=n_trials)
            return {"best_params": study.best_params, "best_score": float(study.best_value), "engine": "optuna"}

        best_score = float("-inf")
        best_params: dict[str, float] = {}
        for _ in range(n_trials):
            params = {
                name: random.uniform(bounds[0], bounds[1])
                for name, bounds in search_space.items()
            }
            score = float(objective(params))
            if score > best_score:
                best_score = score
                best_params = params
        return {"best_params": best_params, "best_score": best_score, "engine": "random_fallback"}
