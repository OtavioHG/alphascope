"""Operational runtime status aggregation for AlphaScope services."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from alphascope.config.settings import settings
from alphascope.monitoring.failure_recovery import FailureRecoveryService
from alphascope.monitoring.runtime_metrics import RuntimeMetricsService
from alphascope.storage.repositories import StorageRepository


class RuntimeStatusService:
    """Aggregate current runtime status from daemon, scheduler and simulation layers."""

    def __init__(
        self,
        *,
        repository: StorageRepository | None = None,
        daemon_status_path: Path | None = None,
        scheduler_status_path: Path | None = None,
        continuous_status_path: Path | None = None,
        heartbeat_path: Path | None = None,
        live_simulated_status_path: Path | None = None,
        runtime_metrics: RuntimeMetricsService | None = None,
        failure_recovery: FailureRecoveryService | None = None,
    ) -> None:
        self.repository = repository or StorageRepository()
        self.daemon_status_path = daemon_status_path or settings.daemon_status_file
        self.scheduler_status_path = scheduler_status_path or settings.runtime_dir / "scheduler_status.json"
        self.continuous_status_path = continuous_status_path or settings.runtime_dir / "continuous_pipeline_status.json"
        self.heartbeat_path = heartbeat_path or settings.heartbeat_file
        self.live_simulated_status_path = live_simulated_status_path or settings.runtime_dir / "live_simulated_status.json"
        self.multi_agent_status_path = settings.runtime_dir / "multi_agent_runtime_status.json"
        self.multi_agent_scheduler_path = settings.runtime_dir / "multi_agent_scheduler_status.json"
        self.multi_agent_heartbeat_path = settings.runtime_dir / "multi_agent_heartbeat.json"
        self.runtime_metrics = runtime_metrics or RuntimeMetricsService()
        self.failure_recovery = failure_recovery or FailureRecoveryService(
            pid_file=settings.daemon_pid_file,
            heartbeat_file=self.heartbeat_path,
        )

    def get_status(self, *, interval: str | None = None) -> dict[str, Any]:
        """Return aggregated runtime status for CLI and TUI output."""
        effective_interval = interval or settings.default_interval
        ranking = self.repository.get_latest_ranking(interval=effective_interval)
        snapshot = self.repository.get_latest_snapshot()

        payload = {
            "daemon": self._read_json(self.daemon_status_path),
            "scheduler": self._read_json(self.scheduler_status_path),
            "continuous_pipeline": self._read_json(self.continuous_status_path),
            "heartbeat": self._read_json(self.heartbeat_path),
            "live_simulated": self._read_json(self.live_simulated_status_path),
            "multi_agent": self._read_json(self.multi_agent_status_path),
            "multi_agent_scheduler": self._read_json(self.multi_agent_scheduler_path),
            "multi_agent_heartbeat": self._read_json(self.multi_agent_heartbeat_path),
            "database": {
                "sqlite_path": str(settings.sqlite_path),
                "exists": settings.sqlite_path.exists(),
            },
            "apis": settings.api_status_summary(),
            "latest_ranking": self._ranking_summary(ranking),
            "latest_snapshot": self._snapshot_summary(snapshot),
            "jobs": self._job_summary(self._read_json(self.scheduler_status_path)),
            "cycles": self._cycle_summary(
                self._read_json(self.continuous_status_path),
                self._read_json(self.live_simulated_status_path),
            ),
            "runtime_metrics": self.runtime_metrics.summary(),
        }
        payload["recovery"] = self.failure_recovery.inspect(payload)
        return payload

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def _ranking_summary(ranking: pd.DataFrame) -> dict[str, Any]:
        if ranking.empty:
            return {"timestamp": None, "rows": 0, "top_symbol": None, "top_score": None}
        timestamp = ranking.iloc[0].get("timestamp")
        top = ranking.sort_values("rank").iloc[0]
        return {
            "timestamp": str(timestamp) if timestamp is not None else None,
            "rows": len(ranking),
            "top_symbol": top.get("symbol"),
            "top_score": float(top.get("score", 0.0)),
        }

    @staticmethod
    def _snapshot_summary(snapshot: dict[str, object] | None) -> dict[str, Any]:
        if snapshot is None:
            return {"timestamp": None, "equity": None, "cash": None, "open_positions": 0}
        positions = snapshot.get("positions_json", {})
        return {
            "timestamp": snapshot.get("timestamp"),
            "equity": snapshot.get("equity"),
            "cash": snapshot.get("cash"),
            "realized_pnl": snapshot.get("realized_pnl"),
            "unrealized_pnl": snapshot.get("unrealized_pnl"),
            "open_positions": len(positions) if isinstance(positions, dict) else 0,
        }

    @staticmethod
    def _job_summary(scheduler_status: dict[str, Any]) -> dict[str, Any]:
        jobs = scheduler_status.get("jobs", [])
        if not isinstance(jobs, list):
            jobs = []
        return {
            "job_count": len(jobs),
            "total_runs": scheduler_status.get("total_runs", 0),
            "total_failures": scheduler_status.get("total_failures", 0),
        }

    @staticmethod
    def _cycle_summary(continuous_status: dict[str, Any], live_status: dict[str, Any]) -> dict[str, Any]:
        return {
            "continuous_cycles": continuous_status.get("cycles_completed", 0),
            "continuous_errors": continuous_status.get("errors", 0),
            "live_cycles": live_status.get("cycle_number", 0),
            "live_errors": 0 if live_status.get("last_cycle_success", True) else 1,
        }
