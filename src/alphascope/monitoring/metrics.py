from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd


def compute_trading_metrics(trades_df: pd.DataFrame) -> dict[str, float]:
    if trades_df.empty:
        return {
            "closed_trades": 0,
            "realized_pnl": 0.0,
            "win_rate": 0.0,
            "average_pnl": 0.0,
        }

    closed_trades = trades_df
    if "status" in trades_df.columns:
        closed_trades = trades_df.loc[trades_df["status"] != "OPEN"].copy()
    if closed_trades.empty:
        return {
            "closed_trades": 0,
            "realized_pnl": 0.0,
            "win_rate": 0.0,
            "average_pnl": 0.0,
        }

    realized = closed_trades["pnl"].astype(float)
    wins = realized[realized > 0]
    return {
        "closed_trades": int(len(closed_trades)),
        "realized_pnl": float(realized.sum()),
        "win_rate": float(len(wins) / len(realized)) if len(realized) else 0.0,
        "average_pnl": float(realized.mean()) if len(realized) else 0.0,
    }


class MetricsCollector:
    def __init__(self, output_path: str = "logs/metrics.jsonl"):
        self.output_path = Path(output_path)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

    def emit(self, metric_name: str, value: float, labels: dict[str, str] | None = None) -> dict[str, object]:
        payload: dict[str, object] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "metric": metric_name,
            "value": float(value),
            "labels": labels or {},
        }
        with self.output_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, default=str) + "\n")
        return payload

    def recent(self, limit: int = 100) -> list[dict[str, object]]:
        if not self.output_path.exists():
            return []
        lines = self.output_path.read_text(encoding="utf-8").splitlines()[-limit:]
        return [json.loads(line) for line in lines if line.strip()]

    def render_prometheus(self) -> str:
        records = self.recent(limit=500)
        latest: dict[tuple[str, str], dict[str, object]] = {}
        for record in records:
            labels = record.get("labels") or {}
            label_key = json.dumps(labels, sort_keys=True, ensure_ascii=False)
            latest[(str(record["metric"]), label_key)] = record

        output: list[str] = []
        for (_, _), record in sorted(latest.items(), key=lambda item: (item[0][0], item[0][1])):
            metric_name = str(record["metric"])
            labels = record.get("labels") or {}
            label_str = ""
            if labels:
                rendered = ",".join(f'{key}="{value}"' for key, value in sorted(labels.items()))
                label_str = f"{{{rendered}}}"
            output.append(f"{metric_name}{label_str} {record['value']}")
        return "\n".join(output) + ("\n" if output else "")
