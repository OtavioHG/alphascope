from __future__ import annotations

from pathlib import Path

import pandas as pd


class DegradationReportBuilder:
    def __init__(self, output_dir: str = "data/processed/reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def build(self, health: pd.DataFrame) -> dict[str, Path]:
        path = self.output_dir / "strategy_degradation_report.csv"
        text_path = self.output_dir / "strategy_degradation_report.txt"
        health.to_csv(path, index=False)
        degraded = health.loc[health.get("degradation_level", "none") != "none"] if not health.empty else pd.DataFrame()
        lines = [
            "ALPHASCOPE STRATEGY DEGRADATION REPORT",
            "",
            f"Strategies monitored: {len(health)}",
            f"Strategies degraded: {len(degraded)}",
        ]
        text_path.write_text("\n".join(lines), encoding="utf-8")
        return {"csv_path": path, "text_path": text_path}
