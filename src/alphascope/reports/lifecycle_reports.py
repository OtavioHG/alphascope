from __future__ import annotations

from pathlib import Path

import pandas as pd


class LifecycleReportBuilder:
    def __init__(self, output_dir: str = "data/processed/reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def build(self, registry: pd.DataFrame, transitions: pd.DataFrame) -> dict[str, Path]:
        registry_path = self.output_dir / "strategy_lifecycle_registry.csv"
        transitions_path = self.output_dir / "strategy_lifecycle_transitions.csv"
        text_path = self.output_dir / "strategy_lifecycle_report.txt"
        registry.to_csv(registry_path, index=False)
        transitions.to_csv(transitions_path, index=False)
        lines = [
            "ALPHASCOPE STRATEGY LIFECYCLE REPORT",
            "",
            f"Registered strategies: {len(registry)}",
            f"Lifecycle transitions: {len(transitions)}",
        ]
        if not registry.empty and "status" in registry.columns:
            lines.append("")
            lines.append("Status distribution:")
            for status, count in registry["status"].value_counts().items():
                lines.append(f"- {status}: {count}")
        text_path.write_text("\n".join(lines), encoding="utf-8")
        return {"registry_path": registry_path, "transitions_path": transitions_path, "text_path": text_path}
