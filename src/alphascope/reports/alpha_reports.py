from __future__ import annotations

from pathlib import Path

import pandas as pd


class AlphaReportBuilder:
    def __init__(self, output_dir: str = "data/processed/reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def build(
        self,
        ranked_alpha: pd.DataFrame,
        anomalies: pd.DataFrame,
        hypotheses: pd.DataFrame,
    ) -> dict[str, Path]:
        top_alpha = ranked_alpha.head(10)
        top_anomalies = anomalies.head(10)
        top_hypotheses = hypotheses.head(10)

        text = ["ALPHASCOPE ALPHA DISCOVERY REPORT", "", "Top strategies:"]
        if top_alpha.empty:
            text.append("- none")
        else:
            for _, row in top_alpha.iterrows():
                text.append(
                    f"- {row['strategy_id']}: score={row['alpha_discovery_score']:.4f} status={row['promotion_status']}"
                )

        text.append("")
        text.append("Top anomalies:")
        if top_anomalies.empty:
            text.append("- none")
        else:
            for _, row in top_anomalies.iterrows():
                text.append(f"- {row['symbol']} {row['anomaly_type']} score={row['anomaly_score']:.4f}")

        text.append("")
        text.append("Hypotheses:")
        if top_hypotheses.empty:
            text.append("- none")
        else:
            for _, row in top_hypotheses.iterrows():
                text.append(f"- {row['summary']}")

        txt_path = self.output_dir / "alpha_discovery_report.txt"
        csv_path = self.output_dir / "alpha_discovery_ranking.csv"
        txt_path.write_text("\n".join(text), encoding="utf-8")
        ranked_alpha.to_csv(csv_path, index=False)
        return {"text_path": txt_path, "ranking_path": csv_path}
