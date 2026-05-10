from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pandas as pd

from alphascope.alerts.alert_dispatcher import AlertRecord
from alphascope.automation.continuous_pipeline import ContinuousPipeline, ContinuousPipelineConfig


class FakePipeline:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def ingest_market(self, symbols: list[str], intervals: list[str], limit: int) -> list[dict[str, object]]:
        self.calls.append("ingest_market")
        return [{"symbol": symbols[0], "interval": intervals[0], "rows": limit}]

    def build_features(self, symbols: list[str], interval: str) -> pd.DataFrame:
        self.calls.append("build_features")
        return pd.DataFrame({"symbol": symbols, "interval": interval})

    def rank_assets(self, symbols: list[str], interval: str) -> pd.DataFrame:
        self.calls.append("rank_assets")
        return pd.DataFrame({"symbol": symbols, "score": [0.8 for _ in symbols]})

    def execute_trading_cycle(self, *, ranking: pd.DataFrame, symbols: list[str], interval: str) -> dict[str, object]:
        del ranking, interval
        self.calls.append("execute_trading_cycle")
        return {
            "trades": [{"symbol": symbols[0], "side": "BUY"}],
            "opened": [{"symbol": symbols[0], "side": "BUY"}],
            "closed": [],
            "snapshot": {
                "timestamp": datetime.now(UTC).isoformat(),
                "cash": 9000.0,
                "equity": 10050.0,
                "positions_json": {"BTCUSDT": {"symbol": "BTCUSDT"}},
            },
        }


class FakeNewsBuilder:
    def __init__(self) -> None:
        self.fetch_calls = 0
        self.saved_filenames: list[str] = []

    def fetch_gdelt(self, query: str, max_records: int, days: int) -> pd.DataFrame:
        self.fetch_calls += 1
        return pd.DataFrame({"title": ["Headline"], "description": ["Body"], "timestamp": [datetime.now(UTC).isoformat()]})

    def save_dataset(self, frame: pd.DataFrame, filename: str) -> Path:
        self.saved_filenames.append(filename)
        return Path(filename)


class FakeNewsInference:
    def score_frame(self, news_frame: pd.DataFrame) -> pd.DataFrame:
        scored = news_frame.copy()
        scored["sentiment_score"] = 0.7
        scored["topic_label"] = "market"
        scored["related_asset"] = "BTC"
        scored["impact_score"] = 0.3
        return scored


class FakeRepository:
    def get_latest_snapshot(self) -> dict[str, object]:
        return {
            "cash": 9000.0,
            "equity": 10050.0,
            "positions_json": {"BTCUSDT": {"symbol": "BTCUSDT"}},
        }

    def get_live_account_view(self) -> dict[str, object]:
        return {"account_snapshot": {"total_balance": 10050.0, "free_balance": 9000.0}, "open_positions_count": 1}


class FakeAlertDispatcher:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []

    def top_ranking_changed(self, ranking: pd.DataFrame) -> AlertRecord | None:
        self.calls.append(("top_ranking_changed", ranking))
        return None

    def trade_opened(self, trade: dict[str, object]) -> AlertRecord:
        self.calls.append(("trade_opened", trade))
        return self._record("trade_opened")

    def trade_closed(self, trade: dict[str, object]) -> AlertRecord:
        self.calls.append(("trade_closed", trade))
        return self._record("trade_closed")

    def portfolio_snapshot(self, snapshot: dict[str, object], *, label: str = "Portfolio snapshot") -> AlertRecord:
        self.calls.append(("portfolio_snapshot", {"snapshot": snapshot, "label": label}))
        return self._record("portfolio_snapshot")

    def pipeline_completed(self, payload: dict[str, object]) -> AlertRecord:
        self.calls.append(("pipeline_completed", payload))
        return self._record("pipeline_completed")

    def critical_error(self, *, component: str, error: str, context: dict[str, object] | None = None) -> AlertRecord:
        self.calls.append(("critical_error", {"component": component, "error": error, "context": context}))
        return self._record("critical_error")

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


def _make_local_test_dir(name: str) -> Path:
    path = Path("data/runtime/test_runtime") / f"{name}_{uuid4().hex}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_continuous_pipeline_runs_cycle_and_writes_status() -> None:
    config = ContinuousPipelineConfig(
        cycle_interval_seconds=5,
        news_refresh_interval_seconds=60,
        symbols=["BTCUSDT", "ETHUSDT"],
        timeframe="1h",
        candle_limit=100,
    )
    test_dir = _make_local_test_dir("continuous_cycle")
    state_path = test_dir / "continuous_status.json"
    alert_dispatcher = FakeAlertDispatcher()
    pipeline = ContinuousPipeline(
        config,
        pipeline=FakePipeline(),
        repository=FakeRepository(),  # type: ignore[arg-type]
        news_builder=FakeNewsBuilder(),  # type: ignore[arg-type]
        news_inference=FakeNewsInference(),  # type: ignore[arg-type]
        state_path=state_path,
        alert_dispatcher=alert_dispatcher,  # type: ignore[arg-type]
    )
    pipeline.repository_path_for_scored_news = lambda: test_dir / "scored_news.csv"  # type: ignore[method-assign]

    result = pipeline.run_cycle()

    assert result.success is True
    assert result.market_rows == 100
    assert result.feature_rows == 2
    assert result.ranking_rows == 2
    assert result.trades_executed == 1
    assert result.news_rows == 1

    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["status"] == "running"
    assert state["cycle_number"] == 1
    assert state["last_cycle_success"] is True
    assert state["open_positions"] == 1
    assert [name for name, _ in alert_dispatcher.calls] == [
        "top_ranking_changed",
        "trade_opened",
        "portfolio_snapshot",
        "pipeline_completed",
    ]


def test_continuous_pipeline_respects_news_refresh_interval() -> None:
    fake_pipeline = FakePipeline()
    fake_news_builder = FakeNewsBuilder()
    config = ContinuousPipelineConfig(
        cycle_interval_seconds=5,
        news_refresh_interval_seconds=3600,
        symbols=["BTCUSDT"],
        timeframe="1h",
        candle_limit=50,
    )
    test_dir = _make_local_test_dir("continuous_news_interval")
    continuous = ContinuousPipeline(
        config,
        pipeline=fake_pipeline,
        repository=FakeRepository(),  # type: ignore[arg-type]
        news_builder=fake_news_builder,  # type: ignore[arg-type]
        news_inference=FakeNewsInference(),  # type: ignore[arg-type]
        state_path=test_dir / "continuous_interval_status.json",
    )
    continuous.repository_path_for_scored_news = lambda: test_dir / "scored_news_interval.csv"  # type: ignore[method-assign]

    first = continuous.run_cycle()
    second = continuous.run_cycle()

    assert first.success is True
    assert second.success is True
    assert fake_news_builder.fetch_calls == 1
