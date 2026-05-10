from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path

import pandas as pd
from sqlalchemy.orm import Session

from alphascope.feature_store.feature_registry import FeatureRegistry
from alphascope.storage.migrations.manager import MigrationManager
from alphascope.storage.database import StorageSessionLocal
from alphascope.storage.models.production import FeatureRecord


class FeatureStore:
    def __init__(
        self,
        registry: FeatureRegistry | None = None,
        session: Session | None = None,
        output_dir: str = "data/processed/feature_store",
    ):
        MigrationManager().upgrade()
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.versions_path = self.output_dir / "feature_versions.jsonl"
        self.registry = registry or FeatureRegistry(output_dir=output_dir)
        self.session = session or StorageSessionLocal()

    def store_features(
        self,
        symbol: str,
        timestamp: datetime,
        features: dict[str, float],
        feature_version: str = "v1",
        dataset_hash: str | None = None,
    ) -> int:
        stored = 0
        for name, value in features.items():
            if self.registry.get(name) is None:
                continue
            record = FeatureRecord(
                symbol=symbol,
                feature_name=name,
                feature_value=float(value),
                timestamp=timestamp,
                online_ready=True,
            )
            self.session.add(record)
            self._record_feature_version(
                feature_name=name,
                feature_version=feature_version,
                symbol=symbol,
                timestamp=timestamp,
                dataset_hash=dataset_hash,
            )
            stored += 1
        self.session.commit()
        return stored

    def load_features(self, symbol: str, feature_names: list[str] | None = None, limit: int = 500) -> pd.DataFrame:
        query = self.session.query(FeatureRecord).filter(FeatureRecord.symbol == symbol).order_by(FeatureRecord.timestamp.desc())
        if feature_names:
            query = query.filter(FeatureRecord.feature_name.in_(feature_names))
        rows = query.limit(limit).all()
        if not rows:
            return pd.DataFrame()
        frame = pd.DataFrame(
            [
                {
                    "symbol": row.symbol,
                    "feature_name": row.feature_name,
                    "feature_value": row.feature_value,
                    "timestamp": row.timestamp,
                }
                for row in rows
            ]
        )
        frame["timestamp"] = pd.to_datetime(frame["timestamp"], errors="coerce", utc=True)
        return frame

    def close(self) -> None:
        self.session.close()

    def feature_metadata(self) -> pd.DataFrame:
        return self.registry.to_frame()

    def feature_versions(self, limit: int = 500) -> pd.DataFrame:
        if not self.versions_path.exists():
            return pd.DataFrame()
        rows = [
            json.loads(line)
            for line in self.versions_path.read_text(encoding="utf-8").splitlines()[-limit:]
            if line.strip()
        ]
        return pd.DataFrame(rows)

    def _record_feature_version(
        self,
        feature_name: str,
        feature_version: str,
        symbol: str,
        timestamp: datetime,
        dataset_hash: str | None,
    ) -> None:
        payload = {
            "feature_name": feature_name,
            "feature_version": feature_version,
            "symbol": symbol,
            "timestamp": timestamp.isoformat(),
            "dataset_hash": dataset_hash,
            "recorded_at": datetime.now(UTC).isoformat(),
        }
        with self.versions_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload) + "\n")
