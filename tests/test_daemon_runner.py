from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from alphascope.alerts.alert_dispatcher import AlertRecord
from alphascope.automation.daemon_runner import DaemonRunner, DaemonRunnerConfig
from alphascope.automation.heartbeat import HeartbeatConfig, HeartbeatService


def _make_local_test_dir(name: str) -> Path:
    path = Path("data/runtime/test_runtime") / f"{name}_{uuid4().hex}"
    path.mkdir(parents=True, exist_ok=True)
    return path


@dataclass
class FakeCycleResult:
    success: bool = True


class FakeContinuousPipeline:
    def __init__(self) -> None:
        self.run_cycle_calls = 0
        self.stop_calls = 0

    def run_cycle(self) -> FakeCycleResult:
        self.run_cycle_calls += 1
        return FakeCycleResult(success=True)

    def stop(self) -> None:
        self.stop_calls += 1

    def get_state(self) -> dict[str, object]:
        return {"status": "stopped" if self.stop_calls else "running", "cycles_completed": self.run_cycle_calls}


class FakeScheduler:
    def __init__(self) -> None:
        self.run_pending_calls = 0
        self.stop_calls = 0

    def run_pending(self) -> None:
        self.run_pending_calls += 1

    def stop(self) -> None:
        self.stop_calls += 1

    def get_state(self) -> dict[str, object]:
        return {"status": "stopped" if self.stop_calls else "running", "run_pending_calls": self.run_pending_calls}


class FakeAlertDispatcher:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []

    def critical_error(self, *, component: str, error: str, context: dict[str, object] | None = None) -> AlertRecord:
        self.calls.append(("critical_error", {"component": component, "error": error, "context": context}))
        return self._record("critical_error")

    def daemon_stopped(self, payload: dict[str, object]) -> AlertRecord:
        self.calls.append(("daemon_stopped", payload))
        return self._record("daemon_stopped")

    @staticmethod
    def _record(alert_type: str) -> AlertRecord:
        return AlertRecord(
            alert_type=alert_type,
            title=alert_type,
            message=alert_type,
            payload={},
            created_at=datetime.now(UTC).isoformat(),
            delivered=True,
        )


def test_heartbeat_service_writes_file() -> None:
    test_dir = _make_local_test_dir("heartbeat")
    heartbeat_file = test_dir / "heartbeat.json"
    service = HeartbeatService(
        HeartbeatConfig(interval_seconds=1, heartbeat_file=heartbeat_file),
        payload_provider=lambda: {"component": "test"},
    )

    service.write_once()

    payload = json.loads(heartbeat_file.read_text(encoding="utf-8"))
    assert payload["status"] == "running"
    assert payload["component"] == "test"
    assert "process_id" in payload


def test_daemon_runner_start_stop_persists_status() -> None:
    test_dir = _make_local_test_dir("daemon_start_stop")
    config = DaemonRunnerConfig(
        symbols=["BTCUSDT", "ETHUSDT"],
        timeframe="1h",
        candle_limit=100,
        cycle_interval_seconds=1,
        news_refresh_interval_seconds=5,
        heartbeat_interval_seconds=1,
        pid_file=test_dir / "alphascope.pid",
        status_file=test_dir / "daemon_status.json",
        heartbeat_file=test_dir / "heartbeat.json",
    )
    daemon = DaemonRunner(
        config,
        scheduler=FakeScheduler(),  # type: ignore[arg-type]
        continuous_pipeline=FakeContinuousPipeline(),  # type: ignore[arg-type]
        alert_dispatcher=FakeAlertDispatcher(),  # type: ignore[arg-type]
    )

    result = daemon.start(max_cycles=2)

    assert result["status"] == "stopped"
    assert result["cycle_count"] == 2
    assert config.status_file.exists()
    assert config.heartbeat_file.exists()
    assert not config.pid_file.exists()

    payload = json.loads(config.status_file.read_text(encoding="utf-8"))
    assert payload["status"] == "stopped"
    assert payload["cycle_count"] == 2


def test_daemon_runner_graceful_shutdown_via_request_stop() -> None:
    test_dir = _make_local_test_dir("daemon_graceful_shutdown")
    config = DaemonRunnerConfig(
        symbols=["BTCUSDT"],
        timeframe="1h",
        candle_limit=50,
        cycle_interval_seconds=1,
        news_refresh_interval_seconds=5,
        heartbeat_interval_seconds=1,
        pid_file=test_dir / "alphascope.pid",
        status_file=test_dir / "daemon_status.json",
        heartbeat_file=test_dir / "heartbeat.json",
    )
    fake_scheduler = FakeScheduler()
    fake_pipeline = FakeContinuousPipeline()
    fake_alerts = FakeAlertDispatcher()
    daemon = DaemonRunner(
        config,
        scheduler=fake_scheduler,  # type: ignore[arg-type]
        continuous_pipeline=fake_pipeline,  # type: ignore[arg-type]
        alert_dispatcher=fake_alerts,  # type: ignore[arg-type]
    )

    result_holder: dict[str, object] = {}

    def _run() -> None:
        result_holder["result"] = daemon.start(run_duration_seconds=10)

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    time.sleep(0.2)
    daemon.request_stop()
    thread.join(timeout=5)

    assert thread.is_alive() is False
    assert fake_scheduler.stop_calls >= 1
    assert fake_pipeline.stop_calls >= 1
    assert config.status_file.exists()

    payload = json.loads(config.status_file.read_text(encoding="utf-8"))
    assert payload["status"] == "stopped"

    status = daemon.status()
    assert status["status"] == "stopped"
    assert "heartbeat" in status
    assert any(name == "daemon_stopped" for name, _ in fake_alerts.calls)
