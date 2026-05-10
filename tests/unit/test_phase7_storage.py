from __future__ import annotations

from datetime import UTC, datetime

from alphascope.feature_store.feature_store import FeatureStore
from alphascope.storage.database import StorageBase, storage_engine
from alphascope.storage.migrations.manager import MigrationManager


def _reset_storage() -> None:
    StorageBase.metadata.drop_all(bind=storage_engine)
    StorageBase.metadata.create_all(bind=storage_engine)


def test_migrations_create_storage_schema() -> None:
    StorageBase.metadata.drop_all(bind=storage_engine)
    status = MigrationManager().upgrade()
    assert status == "migrations_applied"


def test_feature_store_persists_registered_features() -> None:
    _reset_storage()
    store = FeatureStore()
    try:
        stored = store.store_features(
            symbol="BTCUSDT",
            timestamp=datetime.now(UTC),
            features={"RSI": 55.2, "MACD": 1.2, "unknown_feature": 9.9},
        )
        loaded = store.load_features("BTCUSDT")
    finally:
        store.close()

    assert stored == 2
    assert set(loaded["feature_name"]) == {"RSI", "MACD"}
