from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from uuid import uuid4


def _make_local_test_dir(name: str) -> Path:
    path = Path("data/runtime/test_runtime") / f"{name}_{uuid4().hex}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _build_env(test_dir: Path) -> dict[str, str]:
    env = os.environ.copy()
    project_root = Path.cwd()
    existing_pythonpath = env.get("PYTHONPATH", "")
    pythonpath_parts = [str((project_root / "src").resolve())]
    if existing_pythonpath:
        pythonpath_parts.append(existing_pythonpath)
    env["PYTHONPATH"] = os.pathsep.join(pythonpath_parts)
    env["DATA_DIR"] = str((test_dir / "data").as_posix())
    env["LOG_DIR"] = str((test_dir / "logs").as_posix())
    env["SQLITE_PATH"] = str((test_dir / "data" / "alphascope.db").as_posix())
    env["DAEMON_PID_FILE"] = str((test_dir / "alphascope.pid").as_posix())
    env["DAEMON_STATUS_FILE"] = str((test_dir / "daemon_status.json").as_posix())
    env["HEARTBEAT_FILE"] = str((test_dir / "heartbeat.json").as_posix())
    env["COLUMNS"] = "200"
    return env


def test_runtime_status_command_via_subprocess() -> None:
    test_dir = _make_local_test_dir("cli_runtime_status")
    env = _build_env(test_dir)

    (test_dir / "daemon_status.json").write_text(json.dumps({"status": "running", "pid": 4321}), encoding="utf-8")
    (test_dir / "heartbeat.json").write_text(json.dumps({"status": "running", "timestamp": "2026-03-25T12:00:00+00:00"}), encoding="utf-8")
    (test_dir / "scheduler_status.json").write_text(json.dumps({"jobs": [], "total_runs": 1, "total_failures": 0}), encoding="utf-8")
    (test_dir / "continuous_pipeline_status.json").write_text(json.dumps({"cycles_completed": 2, "errors": 0}), encoding="utf-8")
    (test_dir / "live_simulated_status.json").write_text(json.dumps({"cycle_number": 1, "last_cycle_success": True}), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "-m", "alphascope.cli", "runtime-status"],
        cwd=Path.cwd(),
        env=env,
        text=True,
        capture_output=True,
        timeout=30,
    )

    assert result.returncode == 0
    assert "Runtime Overview" in result.stdout
    assert "Infrastructure" in result.stdout


def test_show_jobs_and_status_daemon_commands_via_subprocess() -> None:
    test_dir = _make_local_test_dir("cli_show_jobs")
    env = _build_env(test_dir)

    scheduler_payload = {
        "jobs": [
            {
                "name": "market_ingestion_job",
                "enabled": True,
                "interval_seconds": 300,
                "total_runs": 4,
                "successful_runs": 4,
                "failed_runs": 0,
                "consecutive_failures": 0,
                "next_run_at": "2026-03-25T12:30:00+00:00",
                "last_error": None,
            }
        ],
        "total_runs": 4,
        "total_failures": 0,
    }
    (test_dir / "scheduler_status.json").write_text(json.dumps(scheduler_payload), encoding="utf-8")
    (test_dir / "daemon_status.json").write_text(json.dumps({"status": "running", "pid": 1234}), encoding="utf-8")
    (test_dir / "heartbeat.json").write_text(json.dumps({"status": "running", "timestamp": "2026-03-25T12:00:00+00:00"}), encoding="utf-8")

    show_jobs = subprocess.run(
        [sys.executable, "-m", "alphascope.cli", "show-jobs", "--path", str((test_dir / "scheduler_status.json").as_posix())],
        cwd=Path.cwd(),
        env=env,
        text=True,
        capture_output=True,
        timeout=30,
    )
    status_daemon = subprocess.run(
        [sys.executable, "-m", "alphascope.cli", "status-daemon"],
        cwd=Path.cwd(),
        env=env,
        text=True,
        capture_output=True,
        timeout=30,
    )

    assert show_jobs.returncode == 0
    assert "Scheduler Jobs" in show_jobs.stdout
    assert "market_ingestion_job" in show_jobs.stdout
    assert status_daemon.returncode == 0
    assert "Runtime Overview" in status_daemon.stdout


def test_stop_daemon_command_via_subprocess() -> None:
    test_dir = _make_local_test_dir("cli_stop_daemon")
    env = _build_env(test_dir)
    pid_file = test_dir / "alphascope.pid"

    sleeper = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(60)"],
        cwd=Path.cwd(),
        env=env,
    )
    try:
        pid_file.write_text(str(sleeper.pid), encoding="utf-8")
        result = subprocess.run(
            [sys.executable, "-m", "alphascope.cli", "stop-daemon", "--pid-file", str(pid_file.as_posix())],
            cwd=Path.cwd(),
            env=env,
            text=True,
            capture_output=True,
            timeout=30,
        )

        deadline = time.time() + 10
        while sleeper.poll() is None and time.time() < deadline:
            time.sleep(0.1)

        assert result.returncode == 0
        assert "Sinal de parada enviado" in result.stdout
        assert sleeper.poll() is not None
    finally:
        if sleeper.poll() is None:
            sleeper.kill()
