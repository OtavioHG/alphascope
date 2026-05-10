"""Operational scheduler for recurring AlphaScope jobs."""

from __future__ import annotations

import json
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

import schedule

from alphascope.automation.job_registry import JobDefinition, JobExecutionResult, JobRegistry
from alphascope.core.logger import get_logger

logger = get_logger(__name__)

JobCallable = Callable[[], Any]


class AutomationScheduler:
    """Register and execute recurring jobs with retry and persisted state."""

    def __init__(
        self,
        pipeline: object | None = None,
        *,
        job_registry: JobRegistry | None = None,
        scheduler_engine: schedule.Scheduler | None = None,
        state_path: str | Path | None = None,
    ) -> None:
        self.pipeline = pipeline
        self.scheduler = scheduler_engine or schedule.Scheduler()
        self.job_registry = job_registry or JobRegistry()
        self.state_path = Path(state_path) if state_path else Path("data/runtime/scheduler_status.json")
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self._stop_event = threading.Event()
        self._write_state({"status": "initialized", "updated_at": self._now_iso()})

    def register_job(
        self,
        *,
        name: str,
        func: JobCallable,
        interval_seconds: int,
        tags: tuple[str, ...] = (),
        max_retries: int = 0,
        retry_backoff_seconds: int = 5,
        enabled: bool = True,
        description: str | None = None,
    ) -> JobDefinition:
        """Register a recurring job and schedule it for execution."""
        job = JobDefinition(
            name=name,
            func=func,
            interval_seconds=interval_seconds,
            tags=tags,
            max_retries=max_retries,
            retry_backoff_seconds=retry_backoff_seconds,
            enabled=enabled,
            description=description,
        )
        self.job_registry.register(job)
        scheduled_job = self.scheduler.every(interval_seconds).seconds.do(self._run_registered_job, job.name).tag(*tags, name)
        self.job_registry.update_next_run(job.name, scheduled_job.next_run)
        self._write_state(self._build_state_payload(status="registered"))
        logger.info("Registered job %s every %s seconds", name, interval_seconds)
        return job

    def register_jobs(self) -> None:
        """Register the legacy default automation jobs when a compatible pipeline is available."""
        if self.pipeline is None:
            return

        legacy_jobs: list[tuple[str, str, int, tuple[str, ...]]] = [
            ("market_ingestion_job", "ingest_market_data", 300, ("market",)),
            ("news_ingestion_job", "ingest_news", 600, ("news",)),
            ("feature_job", "build_features", 900, ("features",)),
            ("prediction_job", "predict_assets", 900, ("predict",)),
            ("ranking_job", "rank_assets", 900, ("ranking",)),
            ("paper_trading_job", "execute_paper_trading", 900, ("paper_trading",)),
        ]
        for name, method_name, interval_seconds, tags in legacy_jobs:
            if self.job_registry.exists(name):
                continue
            if not hasattr(self.pipeline, method_name):
                continue
            self.register_job(
                name=name,
                func=getattr(self.pipeline, method_name),
                interval_seconds=interval_seconds,
                tags=tags,
                max_retries=1,
                retry_backoff_seconds=1,
            )

    def register_pipeline_jobs(
        self,
        pipeline: object,
        *,
        market_interval_seconds: int = 300,
        news_interval_seconds: int = 900,
        feature_interval_seconds: int = 300,
        ranking_interval_seconds: int = 300,
        paper_trading_interval_seconds: int = 300,
        max_retries: int = 1,
        retry_backoff_seconds: int = 5,
    ) -> None:
        """Register the new operational jobs for a continuous AlphaScope deployment."""
        self.pipeline = pipeline
        jobs: list[tuple[str, str, int, tuple[str, ...]]] = [
            ("market_ingestion_job", "refresh_market", market_interval_seconds, ("market", "continuous")),
            ("news_ingestion_job", "refresh_news", news_interval_seconds, ("news", "continuous")),
            ("feature_job", "build_features", feature_interval_seconds, ("features", "continuous")),
            ("ranking_job", "build_ranking", ranking_interval_seconds, ("ranking", "continuous")),
            ("paper_trading_job", "run_trading_cycle", paper_trading_interval_seconds, ("paper_trading", "continuous")),
        ]
        for name, method_name, interval_seconds, tags in jobs:
            if self.job_registry.exists(name):
                continue
            if not hasattr(pipeline, method_name):
                continue
            self.register_job(
                name=name,
                func=getattr(pipeline, method_name),
                interval_seconds=interval_seconds,
                tags=tags,
                max_retries=max_retries,
                retry_backoff_seconds=retry_backoff_seconds,
            )

    def run_pending(self) -> None:
        """Run due jobs once and persist scheduler state."""
        if self.get_state().get("status") == "paused":
            return
        self._write_state(self._build_state_payload(status="running", last_tick_at=self._now_iso()))
        self.scheduler.run_pending()
        self._write_state(self._build_state_payload(status="running", last_tick_at=self._now_iso()))

    def run_continuous(
        self,
        *,
        sleep_seconds: float = 1.0,
        duration_seconds: int | None = None,
        iterations: int | None = None,
        stop_event: threading.Event | None = None,
    ) -> None:
        """Run the scheduler loop until duration, iteration limit or stop signal."""
        if not self.scheduler.jobs and self.pipeline is not None:
            self.register_jobs()

        loop_stop_event = stop_event or self._stop_event
        started_at = time.monotonic()
        ticks = 0
        self._write_state(self._build_state_payload(status="running", started_at=self._now_iso()))
        logger.info("Starting scheduler loop with %s jobs", len(self.scheduler.jobs))

        while not loop_stop_event.is_set():
            self.run_pending()
            ticks += 1

            if iterations is not None and ticks >= iterations:
                break
            if duration_seconds is not None and (time.monotonic() - started_at) >= duration_seconds:
                break
            time.sleep(max(0.1, sleep_seconds))

        self._write_state(self._build_state_payload(status="stopped", stopped_at=self._now_iso()))
        logger.info("Scheduler loop stopped")

    def pause(self) -> None:
        """Pause job execution without unregistering jobs."""
        self._write_state(self._build_state_payload(status="paused", paused_at=self._now_iso()))

    def resume(self) -> None:
        """Resume job execution."""
        self._write_state(self._build_state_payload(status="running", resumed_at=self._now_iso()))

    def stop(self) -> None:
        """Signal the continuous loop to stop."""
        self._stop_event.set()
        self._write_state(self._build_state_payload(status="stopping", stopping_at=self._now_iso()))

    def clear(self) -> None:
        """Clear all scheduled jobs and registry state."""
        self.scheduler.clear()
        self.job_registry.clear()
        self._write_state({"status": "cleared", "updated_at": self._now_iso(), "jobs": []})

    def list_jobs(self) -> list[dict[str, Any]]:
        """Return scheduler jobs and their runtime metadata."""
        return self.job_registry.to_dict()

    def get_state(self) -> dict[str, Any]:
        """Read the latest persisted scheduler state."""
        if not self.state_path.exists():
            return {}
        return json.loads(self.state_path.read_text(encoding="utf-8"))

    def _run_registered_job(self, job_name: str) -> None:
        """Execute a registered job with retry and status persistence."""
        job = self.job_registry.get(job_name)
        if not job.enabled:
            logger.info("Skipping disabled job %s", job_name)
            return

        started_at = datetime.now(UTC)
        self.job_registry.mark_started(job_name, started_at)
        logger.info("Starting job %s", job_name)
        last_error: Exception | None = None

        for attempt in range(1, job.max_retries + 2):
            try:
                job.func()
            except Exception as exc:
                last_error = exc
                logger.exception("Job %s failed on attempt %s/%s", job_name, attempt, job.max_retries + 1)
                if attempt <= job.max_retries:
                    time.sleep(max(0, job.retry_backoff_seconds))
                    continue
                finished_at = datetime.now(UTC)
                result = JobExecutionResult(
                    job_name=job_name,
                    success=False,
                    started_at=started_at,
                    finished_at=finished_at,
                    duration_seconds=(finished_at - started_at).total_seconds(),
                    error_message=str(exc),
                    attempts=attempt,
                )
                self.job_registry.record_result(job_name, result)
                self._sync_next_run(job_name)
                self._write_state(self._build_state_payload(status="running", last_error=str(last_error), last_error_at=self._now_iso()))
                return
            else:
                finished_at = datetime.now(UTC)
                result = JobExecutionResult(
                    job_name=job_name,
                    success=True,
                    started_at=started_at,
                    finished_at=finished_at,
                    duration_seconds=(finished_at - started_at).total_seconds(),
                    error_message=None,
                    attempts=attempt,
                )
                self.job_registry.record_result(job_name, result)
                self._sync_next_run(job_name)
                self._write_state(self._build_state_payload(status="running"))
                logger.info("Job %s completed in %.2fs", job_name, result.duration_seconds)
                return

    def _sync_next_run(self, job_name: str) -> None:
        """Sync the next scheduled execution with registry metadata."""
        scheduled_job = next((item for item in self.scheduler.jobs if job_name in item.tags), None)
        if scheduled_job is not None:
            self.job_registry.update_next_run(job_name, scheduled_job.next_run)

    def _build_state_payload(self, *, status: str, **extra: Any) -> dict[str, Any]:
        """Build a scheduler status payload."""
        return {
            "status": status,
            "updated_at": self._now_iso(),
            "job_count": len(self.job_registry.all()),
            "total_runs": self.job_registry.total_runs,
            "total_failures": self.job_registry.total_failures,
            "jobs": self.job_registry.to_dict(),
            **extra,
        }

    def _write_state(self, payload: dict[str, Any]) -> None:
        state = self.get_state()
        state.update(payload)
        self.state_path.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(UTC).isoformat()
