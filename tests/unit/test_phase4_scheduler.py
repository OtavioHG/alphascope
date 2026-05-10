from __future__ import annotations

from datetime import datetime, timedelta

from alphascope.automation.scheduler import AutomationScheduler


class DummyPipeline:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def ingest_market_data(self):
        self.calls.append("market")

    def ingest_news(self):
        self.calls.append("news")

    def build_features(self):
        self.calls.append("features")

    def predict_assets(self):
        self.calls.append("predict")

    def rank_assets(self):
        self.calls.append("ranking")

    def execute_paper_trading(self):
        self.calls.append("paper_trading")


def test_scheduler_registers_and_runs_jobs() -> None:
    pipeline = DummyPipeline()
    scheduler = AutomationScheduler(pipeline=pipeline)
    scheduler.register_jobs()

    assert len(scheduler.scheduler.jobs) == 6
    now = datetime.now()
    for job in scheduler.scheduler.jobs:
        job.next_run = now - timedelta(seconds=1)

    scheduler.run_pending()
    assert sorted(pipeline.calls) == ["features", "market", "news", "paper_trading", "predict", "ranking"]
