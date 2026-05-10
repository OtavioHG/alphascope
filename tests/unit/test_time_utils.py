from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pandas as pd

from alphascope.platform.quant_models import PositionContext
from alphascope.utils.time import ensure_utc, ensure_utc_timestamp, safe_utc_diff


def test_ensure_utc_normalizes_naive_datetime() -> None:
    dt = datetime(2026, 4, 12, 10, 30, 0)

    normalized = ensure_utc(dt)

    assert normalized is not None
    assert normalized.tzinfo == timezone.utc
    assert normalized.hour == 10


def test_ensure_utc_normalizes_aware_datetime() -> None:
    dt = datetime(2026, 4, 12, 7, 30, 0, tzinfo=timezone(timedelta(hours=-3)))

    normalized = ensure_utc(dt)

    assert normalized is not None
    assert normalized.tzinfo == timezone.utc
    assert normalized.hour == 10


def test_ensure_utc_normalizes_string_datetime() -> None:
    normalized = ensure_utc("2026-04-12T10:30:00Z")

    assert normalized is not None
    assert normalized.tzinfo == timezone.utc
    assert normalized.isoformat() == "2026-04-12T10:30:00+00:00"


def test_ensure_utc_normalizes_pandas_timestamp() -> None:
    normalized = ensure_utc(pd.Timestamp("2026-04-12 10:30:00"))

    assert normalized is not None
    assert normalized.tzinfo == timezone.utc
    assert normalized.isoformat() == "2026-04-12T10:30:00+00:00"


def test_ensure_utc_normalizes_binance_milliseconds() -> None:
    normalized = ensure_utc(1712917800000)

    assert normalized is not None
    assert normalized.tzinfo == timezone.utc
    assert normalized.isoformat() == "2024-04-12T10:30:00+00:00"


def test_ensure_utc_timestamp_normalizes_mixed_series() -> None:
    series = pd.Series(
        [
            datetime(2026, 4, 12, 10, 30, 0),
            "2026-04-12T10:31:00Z",
            pd.Timestamp("2026-04-12T10:32:00-03:00"),
        ]
    )

    normalized = ensure_utc_timestamp(series)

    assert str(normalized.dtype).startswith("datetime64[")
    assert str(normalized.dtype).endswith(", UTC]")
    assert normalized.iloc[0].isoformat() == "2026-04-12T10:30:00+00:00"
    assert normalized.iloc[1].isoformat() == "2026-04-12T10:31:00+00:00"
    assert normalized.iloc[2].isoformat() == "2026-04-12T13:32:00+00:00"


def test_safe_utc_diff_handles_naive_and_aware_comparison() -> None:
    created_at = datetime(2026, 4, 12, 9, 0, 0)
    now_utc = datetime(2026, 4, 12, 10, 30, 0, tzinfo=timezone.utc)

    age = safe_utc_diff(now_utc, created_at)

    assert age == timedelta(hours=1, minutes=30)


def test_position_context_age_is_timezone_safe() -> None:
    position = PositionContext(
        symbol="BTCUSDT",
        entry_price=100.0,
        current_price=105.0,
        quantity=1.0,
        score=0.8,
        current_rank=1,
        best_alternative_score_gap=0.0,
        momentum_score=0.5,
        opened_at=datetime(2026, 4, 12, 8, 0, 0),
        now=datetime(2026, 4, 12, 10, 0, 0, tzinfo=timezone.utc),
    )

    assert position.age == timedelta(hours=2)
