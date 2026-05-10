from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import pandas as pd

from alphascope.cli import build_parser
from alphascope.monitoring.runtime_status import RuntimeStatusService


def _make_local_test_dir(name: str) -> Path:
    path = Path("data/runtime/test_runtime") / f"{name}_{uuid4().hex}"
    path.mkdir(parents=True, exist_ok=True)
    return path


class FakeRepository:
    def get_latest_ranking(self, interval: str) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "timestamp": ["2026-03-25T12:00:00+00:00"],
                "symbol": ["BTCUSDT"],
                "score": [0.88],
                "rank": [1],
            }
        )

    def get_latest_snapshot(self) -> dict[str, object]:
        return {
            "timestamp": "2026-03-25T12:05:00+00:00",
            "equity": 10500.0,
            "cash": 8200.0,
            "realized_pnl": 250.0,
            "unrealized_pnl": 50.0,
            "positions_json": {"BTCUSDT": {"symbol": "BTCUSDT"}},
        }


def test_runtime_status_service_aggregates_files_and_storage() -> None:
    test_dir = _make_local_test_dir("runtime_status")
    daemon_status = test_dir / "daemon_status.json"
    scheduler_status = test_dir / "scheduler_status.json"
    continuous_status = test_dir / "continuous_status.json"
    heartbeat = test_dir / "heartbeat.json"
    live_status = test_dir / "live_status.json"

    daemon_status.write_text(json.dumps({"status": "running", "pid": 1234}), encoding="utf-8")
    scheduler_status.write_text(
        json.dumps({"jobs": [{"name": "market_ingestion_job"}], "total_runs": 8, "total_failures": 1}),
        encoding="utf-8",
    )
    continuous_status.write_text(json.dumps({"cycles_completed": 5, "errors": 1}), encoding="utf-8")
    heartbeat.write_text(json.dumps({"status": "running", "timestamp": "2026-03-25T12:10:00+00:00"}), encoding="utf-8")
    live_status.write_text(json.dumps({"cycle_number": 3, "last_cycle_success": True}), encoding="utf-8")

    status = RuntimeStatusService(
        repository=FakeRepository(),  # type: ignore[arg-type]
        daemon_status_path=daemon_status,
        scheduler_status_path=scheduler_status,
        continuous_status_path=continuous_status,
        heartbeat_path=heartbeat,
        live_simulated_status_path=live_status,
    ).get_status(interval="1h")

    assert status["daemon"]["status"] == "running"
    assert status["jobs"]["job_count"] == 1
    assert status["latest_ranking"]["top_symbol"] == "BTCUSDT"
    assert status["latest_snapshot"]["open_positions"] == 1
    assert status["cycles"]["continuous_cycles"] == 5
    assert status["cycles"]["live_cycles"] == 3


def test_cli_parser_recognizes_runtime_commands() -> None:
    parser = build_parser()

    commands = [
        parser.parse_args(["run-continuous", "--symbols", "BTCUSDT", "--cycle-seconds", "5"]),
        parser.parse_args(["schedule-jobs", "--symbols", "BTCUSDT", "--duration-seconds", "5"]),
        parser.parse_args(["show-jobs"]),
        parser.parse_args(["start-daemon", "--symbols", "BTCUSDT"]),
        parser.parse_args(["stop-daemon"]),
        parser.parse_args(["status-daemon"]),
        parser.parse_args(["runtime-status"]),
        parser.parse_args(["run-live-simulated", "--symbols", "BTCUSDT"]),
    ]

    assert [item.command for item in commands] == [
        "run-continuous",
        "schedule-jobs",
        "show-jobs",
        "start-daemon",
        "stop-daemon",
        "status-daemon",
        "runtime-status",
        "run-live-simulated",
    ]
