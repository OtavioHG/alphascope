from __future__ import annotations

from pathlib import Path

import pandas as pd


class PromotionReportBuilder:
    def __init__(self, output_dir: str = "data/processed/reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def build(self, decisions: pd.DataFrame) -> dict[str, Path]:
        csv_path = self.output_dir / "strategy_promotion_decisions.csv"
        text_path = self.output_dir / "strategy_promotion_report.txt"
        decisions.to_csv(csv_path, index=False)
        lines = [
            "ALPHASCOPE STRATEGY PROMOTION REPORT",
            "",
            f"Decisions: {len(decisions)}",
        ]
        if not decisions.empty and "new_status" in decisions.columns:
            lines.append("")
            lines.append("Decision distribution:")
            for status, count in decisions["new_status"].value_counts().items():
                lines.append(f"- {status}: {count}")
        text_path.write_text("\n".join(lines), encoding="utf-8")
        return {"csv_path": csv_path, "text_path": text_path}
