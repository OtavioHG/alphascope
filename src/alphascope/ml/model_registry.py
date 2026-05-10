"""Simple artifact registry for trained market and NLP models."""

from __future__ import annotations

import json
from pathlib import Path

import joblib

from alphascope.config.settings import settings
from alphascope.ml.schemas import MarketModelMetadata


class ModelRegistry:
    """Persist model artifacts and metadata to disk."""

    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = base_dir or settings.model_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save_market_model(self, model: object, metadata: MarketModelMetadata) -> tuple[Path, Path]:
        artifact_path = Path(metadata.artifact_path)
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        metadata_path = artifact_path.with_suffix(".json")
        joblib.dump(model, artifact_path)
        metadata_path.write_text(json.dumps(metadata.to_dict(), indent=2), encoding="utf-8")
        return artifact_path, metadata_path

    def load_model(self, artifact_path: Path | str) -> object:
        return joblib.load(artifact_path)

    def load_metadata(self, metadata_path: Path | str) -> dict[str, object]:
        return json.loads(Path(metadata_path).read_text(encoding="utf-8"))
