"""Time helpers used across the pipeline."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from typing import Any

import pandas as pd


UTC = timezone.utc


def utc_now() -> datetime:
    """Return current timezone-aware UTC time."""
    return datetime.now(timezone.utc)


def ensure_utc(dt: Any) -> datetime | None:
    """Normalize supported datetime-like values to timezone-aware UTC datetimes."""
    if dt is None:
        return None
    if isinstance(dt, date) and not isinstance(dt, datetime):
        return datetime.combine(dt, time.min, tzinfo=timezone.utc)
    if isinstance(dt, str):
        dt = pd.to_datetime(dt, utc=True, errors="coerce")
    elif isinstance(dt, (int, float)) and not isinstance(dt, bool):
        dt = pd.to_datetime(dt, unit="ms", utc=True, errors="coerce")
    elif hasattr(dt, "to_pydatetime") and not isinstance(dt, datetime):
        dt = dt.to_pydatetime()
    if dt is None or pd.isna(dt):
        return None
    if isinstance(dt, pd.Timestamp):
        if dt.tzinfo is None:
            return dt.tz_localize(timezone.utc).to_pydatetime()
        return dt.tz_convert(timezone.utc).to_pydatetime()
    if isinstance(dt, datetime):
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    raise TypeError(f"Unsupported datetime-like value: {type(dt)!r}")


def from_milliseconds(value: int | float) -> pd.Timestamp:
    """Convert unix milliseconds to UTC pandas timestamp."""
    return pd.to_datetime(int(value), unit="ms", utc=True)


def ensure_utc_timestamp(series: pd.Series) -> pd.Series:
    """Normalize a pandas Series to UTC timestamps."""
    return pd.to_datetime(series, utc=True, errors="coerce")


def normalize_datetime_columns(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Normalize known datetime columns in a DataFrame to UTC."""
    normalized = frame.copy()
    for column in columns:
        if column in normalized.columns:
            normalized[column] = ensure_utc_timestamp(normalized[column])
    return normalized


def safe_utc_diff(later: Any, earlier: Any) -> timedelta:
    """Return a timezone-safe timedelta between two datetime-like values."""
    later_utc = ensure_utc(later)
    earlier_utc = ensure_utc(earlier)
    if later_utc is None or earlier_utc is None:
        return timedelta(0)
    return later_utc - earlier_utc
