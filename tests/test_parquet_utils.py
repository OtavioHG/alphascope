from __future__ import annotations

from pathlib import Path
import shutil

import pandas as pd
import pytest

from alphascope.datasets.parquet_utils import convert_csv_to_parquet, read_dataset


def test_convert_csv_to_parquet_and_read_dataset() -> None:
    pytest.importorskip("pyarrow")
    test_dir = Path("data/test_parquet_utils")
    if test_dir.exists():
        shutil.rmtree(test_dir)
    test_dir.mkdir(parents=True, exist_ok=True)
    try:
        csv_path = test_dir / "market.csv"
        parquet_path = test_dir / "market.parquet"
        pd.DataFrame(
            [
                {"date": "2025-01-01T00:00:00Z", "ticker": "BTCUSDT", "open": 1, "high": 2, "low": 0.5, "close": 1.5, "base_volume": 10},
                {"date": "2025-01-01T01:00:00Z", "ticker": "BTCUSDT", "open": 1.5, "high": 2.5, "low": 1.0, "close": 2.0, "base_volume": 12},
            ]
        ).to_csv(csv_path, index=False)

        output = convert_csv_to_parquet(csv_path, parquet_path, chunk_size=1)
        frames = list(read_dataset(output))

        assert output.exists()
        assert len(frames) == 1
        assert {"timestamp", "symbol", "volume"}.issubset(frames[0].columns)
    finally:
        if test_dir.exists():
            shutil.rmtree(test_dir)
