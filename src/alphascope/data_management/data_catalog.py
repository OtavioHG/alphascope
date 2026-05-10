from __future__ import annotations

from pathlib import Path

import pandas as pd


class DataCatalog:
    def __init__(self, base_dir: str = "data/processed"):
        self.base_dir = Path(base_dir)

    def list_datasets(self) -> pd.DataFrame:
        records: list[dict[str, object]] = []
        for path in sorted(self.base_dir.rglob("*.csv")):
            records.append(
                {
                    "name": path.stem,
                    "path": str(path),
                    "size_bytes": path.stat().st_size,
                    "updated_at": path.stat().st_mtime,
                    "category": path.parent.name,
                }
            )
        return pd.DataFrame(records)
