"""Strategy optimization with Optuna."""

from __future__ import annotations

import json

import pandas as pd

from alphascope.config.settings import settings
from alphascope.core.logger import get_logger
from alphascope.optimization.objective import build_objective
from alphascope.storage.repositories import StorageRepository

logger = get_logger(__name__)

try:
    import optuna
except Exception:  # pragma: no cover - optional dependency
    optuna = None


class StrategyTuner:
    """Run Optuna optimization and persist the best strategy parameters."""

    def __init__(self, repository: StorageRepository | None = None) -> None:
        self.repository = repository or StorageRepository()

    def optimize(self, symbol: str, interval: str, n_trials: int | None = None) -> dict[str, object]:
        if optuna is None:
            raise RuntimeError("optuna is not installed. Install requirements-full.txt to enable optimization.")
        study = optuna.create_study(direction="maximize")
        study.optimize(build_objective(self.repository, symbol=symbol, interval=interval), n_trials=n_trials or settings.optuna_trials)

        params_path = settings.optuna_dir / f"best_params_{symbol}_{interval}.json"
        trials_path = settings.optuna_dir / f"study_trials_{symbol}_{interval}.csv"
        params_path.write_text(
            json.dumps(
                {
                    "symbol": symbol,
                    "interval": interval,
                    "best_value": study.best_value,
                    "best_params": study.best_params,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        pd.DataFrame([trial.params | {"value": trial.value} for trial in study.trials]).to_csv(trials_path, index=False)
        logger.info("Saved Optuna best params to %s", params_path)
        return {
            "best_value": study.best_value,
            "best_params": study.best_params,
            "params_path": str(params_path),
            "trials_path": str(trials_path),
        }
