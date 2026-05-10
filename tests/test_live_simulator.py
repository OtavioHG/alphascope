from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pandas as pd

from alphascope.simulation.event_loop import EventLoop, EventLoopConfig
from alphascope.simulation.live_simulator import LiveSimulationConfig, LiveSimulator


def _make_local_test_dir(name: str) -> Path:
    path = Path("data/runtime/test_runtime") / f"{name}_{uuid4().hex}"
    path.mkdir(parents=True, exist_ok=True)
    return path


class FakeRepository:
    def __init__(self, prices: list[float]) -> None:
        self.prices = prices
        self.price_index = 0
        self.saved_trades: list[dict[str, object]] = []
        self.saved_snapshots: list[dict[str, object]] = []

    def get_candles(self, symbol: str, interval: str, limit: int | None = None) -> pd.DataFrame:
        price = self.prices[min(self.price_index, len(self.prices) - 1)]
        return pd.DataFrame({"close": [price]})

    def save_trades(self, trades: list[dict[str, object]]) -> int:
        self.saved_trades.extend(trades)
        return len(trades)

    def save_snapshot(self, snapshot: dict[str, object]) -> int:
        self.saved_snapshots.append(snapshot)
        return 1

    def get_latest_snapshot(self) -> dict[str, object] | None:
        if not self.saved_snapshots:
            return None
        return self.saved_snapshots[-1]


class FakePipeline:
    def __init__(self, repository: FakeRepository, rankings: list[pd.DataFrame]) -> None:
        self.repository = repository
        self.rankings = rankings
        self.rank_index = 0

    def rank_assets(self, symbols: list[str], interval: str) -> pd.DataFrame:
        ranking = self.rankings[min(self.rank_index, len(self.rankings) - 1)]
        self.repository.price_index = self.rank_index
        self.rank_index += 1
        return ranking


def test_live_simulator_opens_and_closes_positions_in_live_simulated_mode() -> None:
    test_dir = _make_local_test_dir("live_simulated")
    repository = FakeRepository(prices=[100.0, 120.0])
    pipeline = FakePipeline(
        repository=repository,
        rankings=[
            pd.DataFrame({"symbol": ["BTCUSDT"], "score": [0.8]}),
            pd.DataFrame({"symbol": ["BTCUSDT"], "score": [0.2]}),
        ],
    )
    simulator = LiveSimulator(
        LiveSimulationConfig(
            symbols=["BTCUSDT"],
            timeframe="1h",
            candle_limit=100,
            mode="live_simulated",
            state_path=test_dir / "live_status.json",
        ),
        pipeline=pipeline,  # type: ignore[arg-type]
    )

    first = simulator.run_cycle()
    second = simulator.run_cycle()

    assert first.success is True
    assert first.trades == 1
    assert first.open_positions == 1
    assert second.success is True
    assert second.trades == 1
    assert second.open_positions == 0
    assert len(repository.saved_trades) == 2
    assert len(repository.saved_snapshots) == 2


def test_live_simulator_dry_run_keeps_state_without_persisting_trades() -> None:
    test_dir = _make_local_test_dir("live_dry_run")
    repository = FakeRepository(prices=[100.0])
    pipeline = FakePipeline(
        repository=repository,
        rankings=[pd.DataFrame({"symbol": ["BTCUSDT"], "score": [0.9]})],
    )
    simulator = LiveSimulator(
        LiveSimulationConfig(
            symbols=["BTCUSDT"],
            timeframe="1h",
            candle_limit=100,
            mode="dry_run",
            state_path=test_dir / "dry_run_status.json",
        ),
        pipeline=pipeline,  # type: ignore[arg-type]
    )

    result = simulator.run_cycle()

    assert result.success is True
    assert result.trades == 1
    assert len(repository.saved_trades) == 0
    assert len(repository.saved_snapshots) == 0
    state = json.loads((test_dir / "dry_run_status.json").read_text(encoding="utf-8"))
    assert state["mode"] == "dry_run"
    assert state["trades"] == 1


def test_live_simulator_event_loop_runs_multiple_cycles() -> None:
    test_dir = _make_local_test_dir("live_event_loop")
    repository = FakeRepository(prices=[100.0, 101.0])
    pipeline = FakePipeline(
        repository=repository,
        rankings=[
            pd.DataFrame({"symbol": ["BTCUSDT"], "score": [0.8]}),
            pd.DataFrame({"symbol": ["BTCUSDT"], "score": [0.8]}),
        ],
    )
    simulator = LiveSimulator(
        LiveSimulationConfig(
            symbols=["BTCUSDT"],
            timeframe="1h",
            candle_limit=100,
            mode="dry_run",
            state_path=test_dir / "event_loop_status.json",
        ),
        pipeline=pipeline,  # type: ignore[arg-type]
        event_loop=EventLoop(EventLoopConfig(cycle_interval_seconds=1, run_forever=True)),
    )

    results = simulator.run(max_cycles=2)

    assert len(results) == 2
    assert all(result.success for result in results)
