from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import pandas as pd

from alphascope.monitoring.failure_recovery import FailureRecoveryService
from alphascope.monitoring.metrics import MetricsCollector
from alphascope.monitoring.runtime_metrics import RuntimeMetricsService
from alphascope.monitoring.runtime_status import RuntimeStatusService


def _make_local_test_dir(name: str) -> Path:
    path = Path("data/runtime/test_runtime") / f"{name}_{uuid4().hex}"
    path.mkdir(parents=True, exist_ok=True)
    return path


class FakeRepository:
    def get_latest_ranking(self, interval: str) -> pd.DataFrame:
        return pd.DataFrame({"timestamp": ["2026-03-25T12:00:00+00:00"], "symbol": ["BTCUSDT"], "score": [0.77], "rank": [1]})

    def get_latest_snapshot(self) -> dict[str, object]:
        return {
            "timestamp": "2026-03-25T12:10:00+00:00",
            "equity": 10100.0,
            "cash": 9000.0,
            "realized_pnl": 80.0,
            "unrealized_pnl": 20.0,
            "positions_json": {"BTCUSDT": {"symbol": "BTCUSDT"}},
        }


def test_runtime_metrics_service_summarizes_recent_metrics() -> None:
    test_dir = _make_local_test_dir("runtime_metrics")
    collector = MetricsCollector(output_path=str(test_dir / "metrics.jsonl"))
    collector.emit("pipeline_duration", 12.5, {"source": "continuous"})
    collector.emit("system_errors", 1.0, {"source": "daemon"})
    collector.emit("pipeline_duration", 8.0, {"source": "continuous"})

    summary = RuntimeMetricsService(metrics_collector=collector).summary()

    assert summary["records"] == 3
    assert summary["latest_values"]["pipeline_duration"] == 8.0
    assert summary["counts"]["pipeline_duration"] == 2
    assert summary["sums"]["pipeline_duration"] == 20.5


def test_failure_recovery_detects_stale_pid_and_invalid_heartbeat() -> None:
    test_dir = _make_local_test_dir("failure_recovery")
    pid_file = test_dir / "alphascope.pid"
    heartbeat_file = test_dir / "heartbeat.json"
    pid_file.write_text("999999", encoding="utf-8")
    heartbeat_file.write_text(json.dumps({"timestamp": "not-a-date"}), encoding="utf-8")

    service = FailureRecoveryService(pid_file=pid_file, heartbeat_file=heartbeat_file, max_consecutive_errors=2, heartbeat_stale_seconds=1)
    result = service.inspect({"daemon": {"status": "error", "last_error": "boom", "consecutive_errors": 2}, "continuous_pipeline": {"errors": 2}, "heartbeat": {"timestamp": "not-a-date"}})

    issue_codes = {item["code"] for item in result["issues"]}
    assert result["healthy"] is False
    assert {"stale_pid", "invalid_heartbeat", "excessive_errors", "daemon_error"}.issubset(issue_codes)


def test_runtime_status_service_includes_metrics_and_recovery() -> None:
    test_dir = _make_local_test_dir("runtime_status_monitoring")
    daemon_status = test_dir / "daemon_status.json"
    scheduler_status = test_dir / "scheduler_status.json"
    continuous_status = test_dir / "continuous_status.json"
    heartbeat = test_dir / "heartbeat.json"
    live_status = test_dir / "live_status.json"
    pid_file = test_dir / "alphascope.pid"
    metrics_path = test_dir / "metrics.jsonl"

    daemon_status.write_text(json.dumps({"status": "running", "pid": 1234, "consecutive_errors": 0}), encoding="utf-8")
    scheduler_status.write_text(json.dumps({"jobs": [], "total_runs": 3, "total_failures": 0}), encoding="utf-8")
    continuous_status.write_text(json.dumps({"cycles_completed": 4, "errors": 0}), encoding="utf-8")
    heartbeat.write_text(json.dumps({"status": "running", "timestamp": "2026-03-25T12:10:00+00:00"}), encoding="utf-8")
    live_status.write_text(json.dumps({"cycle_number": 2, "last_cycle_success": True}), encoding="utf-8")
    pid_file.write_text("not-a-pid", encoding="utf-8")

    collector = MetricsCollector(output_path=str(metrics_path))
    collector.emit("pipeline_duration", 6.0)

    service = RuntimeStatusService(
        repository=FakeRepository(),  # type: ignore[arg-type]
        daemon_status_path=daemon_status,
        scheduler_status_path=scheduler_status,
        continuous_status_path=continuous_status,
        heartbeat_path=heartbeat,
        live_simulated_status_path=live_status,
        runtime_metrics=RuntimeMetricsService(metrics_collector=collector),
        failure_recovery=FailureRecoveryService(pid_file=pid_file, heartbeat_file=heartbeat, heartbeat_stale_seconds=10**9),
    )
    status = service.get_status(interval="1h")

    assert status["runtime_metrics"]["latest_values"]["pipeline_duration"] == 6.0
    assert status["recovery"]["healthy"] is False
    issue_codes = {item["code"] for item in status["recovery"]["issues"]}
    assert "invalid_pid" in issue_codes
