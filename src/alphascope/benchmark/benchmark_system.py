from __future__ import annotations

from pathlib import Path

import pandas as pd


class BenchmarkSystem:
    def __init__(self, output_dir: str = "data/processed/benchmarks"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def compare(self, candidates: pd.DataFrame, benchmark_columns: list[str]) -> pd.DataFrame:
        if candidates.empty:
            return pd.DataFrame()
        columns = [column for column in benchmark_columns if column in candidates.columns]
        result = candidates[["strategy_id"] + columns].copy() if "strategy_id" in candidates.columns else candidates[columns].copy()
        if columns:
            result["benchmark_score"] = result[columns].sum(axis=1)
        else:
            result["benchmark_score"] = 0.0
        result = result.sort_values("benchmark_score", ascending=False).reset_index(drop=True)
        result.to_csv(self.output_dir / "benchmark_results.csv", index=False)
        return result
