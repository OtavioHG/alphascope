from __future__ import annotations

from pathlib import Path

import pandas as pd

from alphascope.config.settings import settings
from alphascope.storage.repositories import StorageRepository


class RankingService:
    def __init__(
        self,
        repository: StorageRepository | None = None,
        interval: str | None = None,
        rankings_dir: str | Path | None = None,
        predictions_dir: str | Path | None = None,
        dataset_path: str | Path | None = None,
    ):
        self.repository = repository or StorageRepository()
        self.interval = interval or settings.default_interval
        self.rankings_dir = Path(rankings_dir) if rankings_dir else None
        self.predictions_dir = Path(predictions_dir) if predictions_dir else None
        self.dataset_path = Path(dataset_path) if dataset_path else None

    def load_latest_ranking(self) -> pd.DataFrame:
        if self.rankings_dir is not None:
            ranking_files = sorted(self.rankings_dir.glob("ranking_*.csv"), key=lambda item: item.stat().st_mtime)
            if not ranking_files:
                return pd.DataFrame()
            ranking = pd.read_csv(ranking_files[-1])
            if self.predictions_dir is not None:
                prediction_files = sorted(self.predictions_dir.glob("predictions_*.csv"), key=lambda item: item.stat().st_mtime)
                if prediction_files:
                    predictions = pd.read_csv(prediction_files[-1])
                    ranking = ranking.merge(predictions, on="symbol", how="left")
            if "timestamp" in ranking.columns:
                ranking["timestamp"] = pd.to_datetime(ranking["timestamp"], errors="coerce", utc=True)
            return ranking
        ranking = self.repository.get_latest_ranking(self.interval)
        if ranking.empty:
            return ranking
        if "timestamp" in ranking.columns:
            ranking["timestamp"] = pd.to_datetime(ranking["timestamp"], errors="coerce", utc=True)
        return ranking.sort_values("rank").reset_index(drop=True)

    def filter_ranking(self, minimum_score: float = 0.0, maximum_risk: float = 1.0) -> pd.DataFrame:
        ranking = self.load_latest_ranking()
        if ranking.empty:
            return ranking
        score_column = "score" if "score" in ranking.columns else "score_final"
        ranking = ranking.loc[pd.to_numeric(ranking[score_column], errors="coerce").fillna(0.0) >= minimum_score].copy()
        risk_column = "risk_score" if "risk_score" in ranking.columns else "score_risk"
        if risk_column in ranking.columns:
            ranking = ranking.loc[pd.to_numeric(ranking[risk_column], errors="coerce").fillna(0.0) <= maximum_risk].copy()
        return ranking.reset_index(drop=True)
