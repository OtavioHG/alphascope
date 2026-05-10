from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

from alphascope.automation.scheduler import AutomationScheduler


def _make_local_test_dir(name: str) -> Path:
    path = Path("data/runtime/test_runtime") / f"{name}_{uuid4().hex}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_scheduler_retries_failed_job_and_persists_state() -> None:
    attempts = {"count": 0}

    def flaky_job() -> None:
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise RuntimeError("temporary failure")

    state_path = _make_local_test_dir("scheduler_retry") / "scheduler_status.json"
    scheduler = AutomationScheduler(state_path=state_path)
    scheduler.register_job(
        name="flaky_job",
        func=flaky_job,
        interval_seconds=1,
        max_retries=1,
        retry_backoff_seconds=0,
    )

    scheduler.scheduler.jobs[0].next_run = datetime.now() - timedelta(seconds=1)
    scheduler.run_pending()

    assert attempts["count"] == 2
    jobs = scheduler.list_jobs()
    assert len(jobs) == 1
    assert jobs[0]["name"] == "flaky_job"
    assert jobs[0]["successful_runs"] == 1
    assert jobs[0]["failed_runs"] == 0
    assert jobs[0]["last_attempts"] == 2

    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["status"] == "running"
    assert state["total_runs"] == 1
    assert state["total_failures"] == 0


def test_scheduler_register_jobs_keeps_legacy_compatibility() -> None:
    class LegacyPipeline:
        def __init__(self) -> None:
            self.calls: list[str] = []

        def ingest_market_data(self) -> None:
            self.calls.append("market")

        def ingest_news(self) -> None:
            self.calls.append("news")

        def build_features(self) -> None:
            self.calls.append("features")

        def predict_assets(self) -> None:
            self.calls.append("predict")

        def rank_assets(self) -> None:
            self.calls.append("ranking")

        def execute_paper_trading(self) -> None:
            self.calls.append("paper_trading")

    pipeline = LegacyPipeline()
    scheduler = AutomationScheduler(
        pipeline=pipeline,
        state_path=_make_local_test_dir("scheduler_legacy") / "legacy_scheduler_status.json",
    )
    scheduler.register_jobs()

    assert len(scheduler.scheduler.jobs) == 6
    now = datetime.now()
    for job in scheduler.scheduler.jobs:
        job.next_run = now - timedelta(seconds=1)

    scheduler.run_pending()

    assert sorted(pipeline.calls) == ["features", "market", "news", "paper_trading", "predict", "ranking"]
