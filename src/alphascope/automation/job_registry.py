"""Job registry and runtime metadata for scheduled automation tasks."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Callable

JobCallable = Callable[[], Any]


@dataclass(slots=True)
class JobExecutionResult:
    """Execution outcome for a scheduled job."""

    job_name: str
    success: bool
    started_at: datetime
    finished_at: datetime
    duration_seconds: float
    error_message: str | None = None
    attempts: int = 1


@dataclass(slots=True)
class JobDefinition:
    """Job configuration and current runtime status."""

    name: str
    func: JobCallable
    interval_seconds: int
    tags: tuple[str, ...] = ()
    max_retries: int = 0
    retry_backoff_seconds: int = 5
    enabled: bool = True
    description: str | None = None
    total_runs: int = 0
    successful_runs: int = 0
    failed_runs: int = 0
    consecutive_failures: int = 0
    last_started_at: datetime | None = None
    last_finished_at: datetime | None = None
    last_success_at: datetime | None = None
    last_error: str | None = None
    last_duration_seconds: float | None = None
    last_attempts: int = 0
    next_run_at: datetime | None = None
    history: list[JobExecutionResult] = field(default_factory=list)


class JobRegistry:
    """In-memory registry for jobs and their status."""

    def __init__(self) -> None:
        self._jobs: dict[str, JobDefinition] = {}

    @property
    def total_runs(self) -> int:
        return sum(job.total_runs for job in self._jobs.values())

    @property
    def total_failures(self) -> int:
        return sum(job.failed_runs for job in self._jobs.values())

    def register(self, job: JobDefinition) -> None:
        """Register a job definition."""
        if job.interval_seconds <= 0:
            raise ValueError("interval_seconds must be greater than zero.")
        if job.name in self._jobs:
            raise ValueError(f"Job '{job.name}' is already registered.")
        self._jobs[job.name] = job

    def exists(self, name: str) -> bool:
        """Return whether a job name is already registered."""
        return name in self._jobs

    def get(self, name: str) -> JobDefinition:
        """Return a registered job definition."""
        if name not in self._jobs:
            raise KeyError(f"Unknown job: {name}")
        return self._jobs[name]

    def all(self) -> list[JobDefinition]:
        """Return all registered jobs."""
        return list(self._jobs.values())

    def clear(self) -> None:
        """Remove all registered jobs."""
        self._jobs.clear()

    def mark_started(self, name: str, started_at: datetime) -> None:
        """Mark a job start time."""
        job = self.get(name)
        job.last_started_at = started_at

    def update_next_run(self, name: str, next_run_at: datetime | None) -> None:
        """Persist next run scheduling metadata."""
        job = self.get(name)
        job.next_run_at = next_run_at

    def record_result(self, name: str, result: JobExecutionResult) -> None:
        """Record the execution outcome of a job."""
        job = self.get(name)
        job.total_runs += 1
        job.last_finished_at = result.finished_at
        job.last_duration_seconds = result.duration_seconds
        job.last_attempts = result.attempts
        job.history.append(result)
        if result.success:
            job.successful_runs += 1
            job.consecutive_failures = 0
            job.last_success_at = result.finished_at
            job.last_error = None
        else:
            job.failed_runs += 1
            job.consecutive_failures += 1
            job.last_error = result.error_message

    def to_dict(self) -> list[dict[str, Any]]:
        """Convert the registry into JSON-friendly dictionaries."""
        rows: list[dict[str, Any]] = []
        for job in self.all():
            rows.append(
                {
                    "name": job.name,
                    "interval_seconds": job.interval_seconds,
                    "tags": list(job.tags),
                    "enabled": job.enabled,
                    "description": job.description,
                    "max_retries": job.max_retries,
                    "retry_backoff_seconds": job.retry_backoff_seconds,
                    "total_runs": job.total_runs,
                    "successful_runs": job.successful_runs,
                    "failed_runs": job.failed_runs,
                    "consecutive_failures": job.consecutive_failures,
                    "last_started_at": self._serialize_datetime(job.last_started_at),
                    "last_finished_at": self._serialize_datetime(job.last_finished_at),
                    "last_success_at": self._serialize_datetime(job.last_success_at),
                    "last_error": job.last_error,
                    "last_duration_seconds": job.last_duration_seconds,
                    "last_attempts": job.last_attempts,
                    "next_run_at": self._serialize_datetime(job.next_run_at),
                }
            )
        return rows

    @staticmethod
    def _serialize_datetime(value: datetime | None) -> str | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.astimezone().isoformat()
        return value.astimezone(UTC).isoformat()
