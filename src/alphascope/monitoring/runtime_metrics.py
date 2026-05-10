"""Operational runtime metrics derived from persisted metric/event logs."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from alphascope.config.settings import settings
from alphascope.monitoring.metrics import MetricsCollector


class RuntimeMetricsService:
    """Summarize recent runtime metrics for operational monitoring."""

    def __init__(self, metrics_collector: MetricsCollector | None = None, *, metrics_path: str | Path | None = None) -> None:
        self.metrics_collector = metrics_collector or MetricsCollector(output_path=str(metrics_path or settings.runtime_log_dir / "metrics.jsonl"))

    def summary(self, *, recent_limit: int = 200) -> dict[str, Any]:
        """Return the latest values and aggregates for recent runtime metrics."""
        records = self.metrics_collector.recent(limit=recent_limit)
        latest_by_metric: dict[str, dict[str, object]] = {}
        counts: dict[str, int] = defaultdict(int)
        sums: dict[str, float] = defaultdict(float)

        for record in records:
            metric_name = str(record.get("metric"))
            latest_by_metric[metric_name] = record
            counts[metric_name] += 1
            try:
                sums[metric_name] += float(record.get("value", 0.0))
            except (TypeError, ValueError):
                continue

        latest_values = {name: float(payload.get("value", 0.0)) for name, payload in latest_by_metric.items()}
        return {
            "records": len(records),
            "latest_values": latest_values,
            "counts": dict(counts),
            "sums": {name: round(total, 6) for name, total in sums.items()},
        }
