from __future__ import annotations

from typing import Iterable

import numpy as np

try:
    import alphascope_rust as _alphascope_rust
except Exception:
    _alphascope_rust = None


def rust_backend_available() -> bool:
    return _alphascope_rust is not None


def compute_pct_returns(values: Iterable[float]) -> list[float]:
    series = [float(value) for value in values]
    if _alphascope_rust is not None:
        return list(_alphascope_rust.compute_pct_returns(series))
    if not series:
        return []
    output = [0.0]
    for previous, current in zip(series[:-1], series[1:]):
        output.append((current / previous) - 1.0 if previous else 0.0)
    return output


def rolling_zscore(values: Iterable[float], window: int = 5) -> list[float]:
    series = np.asarray([float(value) for value in values], dtype=float)
    if _alphascope_rust is not None:
        return list(_alphascope_rust.rolling_zscore(series.tolist(), int(window)))
    if len(series) == 0:
        return []
    result = np.zeros_like(series)
    for index in range(len(series)):
        start = max(0, index - window + 1)
        current_window = series[start : index + 1]
        std = current_window.std(ddof=0)
        result[index] = 0.0 if std == 0 else (series[index] - current_window.mean()) / std
    return result.tolist()


def detect_volume_spikes(values: Iterable[float], window: int = 8, threshold: float = 2.0) -> list[bool]:
    zscores = rolling_zscore(values, window=window)
    return [float(score) >= threshold for score in zscores]
