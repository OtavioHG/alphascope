from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from alphascope.config.settings import settings
from alphascope.storage.repositories import StorageRepository


class ModelLifecycleManager:
    def __init__(self, repository: StorageRepository | None = None) -> None:
        self.repository = repository or StorageRepository()
        self._ensure_dirs()

    def register_candidate(
        self,
        *,
        model_name: str,
        metrics: dict[str, Any],
        artifact_path: str,
        metadata_path: str,
        feature_columns: list[str],
        dataset_used: str,
        params: dict[str, Any] | None = None,
        trade_count: int = 0,
        candle_count: int = 0,
    ) -> dict[str, Any]:
        version = f"v{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"
        staged_artifact = self._copy_to_stage(Path(artifact_path), model_name, version, settings.staging_model_dir)
        staged_metadata = self._copy_to_stage(Path(metadata_path), model_name, version, settings.staging_model_dir)
        current = self.repository.get_model_versions(stage="production", limit=1)
        current_metrics = {} if current.empty else dict(current.iloc[0].get("metrics_json", {}) or {})
        promoted = self._should_promote(metrics, current_metrics)
        status = "promoted" if promoted else "rejected"
        stage = "production" if promoted else "archive"
        final_artifact = staged_artifact
        final_metadata = staged_metadata
        rollback_reason = None
        if promoted:
            final_artifact = self._copy_to_stage(staged_artifact, model_name, version, settings.production_model_dir)
            final_metadata = self._copy_to_stage(staged_metadata, model_name, version, settings.production_model_dir)
            self._copy_to_stage(final_artifact, model_name, version, settings.best_model_dir)
            self._copy_to_stage(final_metadata, model_name, version, settings.best_model_dir)
            shutil.copy2(final_artifact, settings.market_model_path)
            shutil.copy2(final_metadata, settings.market_model_path.with_suffix(".json"))
        else:
            rollback_reason = "new_model_underperformed_current_production"
            final_artifact = self._copy_to_stage(staged_artifact, model_name, version, settings.archive_model_dir)
            final_metadata = self._copy_to_stage(staged_metadata, model_name, version, settings.archive_model_dir)
        payload = {
            "model_name": model_name,
            "version": version,
            "stage": stage,
            "status": status,
            "trained_at": datetime.now(UTC),
            "promoted_at": datetime.now(UTC) if promoted else None,
            "artifact_path": str(final_artifact),
            "metadata_path": str(final_metadata),
            "dataset_used": dataset_used,
            "features_used": feature_columns,
            "average_score": float(metrics.get("roc_auc", metrics.get("f1", 0.0))),
            "trade_count": trade_count,
            "candle_count": candle_count,
            "metrics_json": metrics,
            "params_json": params or {},
            "rollback_reason": rollback_reason,
        }
        self.repository.save_model_version(payload)
        return {
            "version": version,
            "promoted": promoted,
            "rollback_triggered": not promoted and not current.empty,
            "artifact_path": str(final_artifact),
            "metadata_path": str(final_metadata),
            "stage": stage,
            "status": status,
        }

    @staticmethod
    def _should_promote(candidate_metrics: dict[str, Any], current_metrics: dict[str, Any]) -> bool:
        if not current_metrics:
            return True
        candidate_score = float(candidate_metrics.get("roc_auc", candidate_metrics.get("f1", 0.0)))
        current_score = float(current_metrics.get("roc_auc", current_metrics.get("f1", 0.0)))
        candidate_accuracy = float(candidate_metrics.get("accuracy", 0.0))
        current_accuracy = float(current_metrics.get("accuracy", 0.0))
        return candidate_score > current_score or (candidate_score == current_score and candidate_accuracy >= current_accuracy)

    @staticmethod
    def _copy_to_stage(path: Path, model_name: str, version: str, target_dir: Path) -> Path:
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / f"{model_name}_{version}{path.suffix}"
        shutil.copy2(path, target)
        return target

    @staticmethod
    def _ensure_dirs() -> None:
        for directory in (
            settings.production_model_dir,
            settings.staging_model_dir,
            settings.archive_model_dir,
            settings.best_model_dir,
            settings.experiments_model_dir,
        ):
            directory.mkdir(parents=True, exist_ok=True)

