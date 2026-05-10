from __future__ import annotations

import pandas as pd
from sqlalchemy.dialects import postgresql

from alphascope.storage.models import MarketCandle
from alphascope.storage.repositories import StorageRepository


class _FakeDialect:
    name = "postgresql"


class _FakeBind:
    dialect = _FakeDialect()


class _FakeSession:
    def __init__(self) -> None:
        self.bind = _FakeBind()
        self.executed = []

    def execute(self, statement) -> None:
        self.executed.append(statement)


def test_bulk_upsert_records_uses_postgres_on_conflict_update() -> None:
    repository = StorageRepository(auto_cleanup=False)
    session = _FakeSession()
    rows = [
        {
            "timestamp": pd.Timestamp("2026-04-15T00:00:00Z").to_pydatetime(),
            "symbol": "BTCUSDT",
            "interval": "1h",
            "open": 100.0,
            "high": 110.0,
            "low": 95.0,
            "close": 105.0,
            "volume": 1234.0,
        }
    ]

    repository._bulk_upsert_records(
        session=session,
        model=MarketCandle,
        records=rows,
        conflict_columns=["timestamp", "symbol", "interval"],
        update_columns=["timestamp", "symbol", "interval", "open", "high", "low", "close", "volume"],
    )

    assert len(session.executed) == 1
    compiled = str(
        session.executed[0].compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )
    assert "ON CONFLICT (timestamp, symbol, interval) DO UPDATE" in compiled
    assert "market_candles" in compiled
    assert "close = excluded.close" in compiled
