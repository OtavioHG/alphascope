from __future__ import annotations

import shutil
from pathlib import Path

import pandas as pd

from alphascope.benchmark.benchmark_system import BenchmarkSystem
from alphascope.data_management.data_catalog import DataCatalog
from alphascope.data_management.data_lineage import DataLineageTracker
from alphascope.data_management.dataset_versioning import DatasetVersionManager
from alphascope.data_management.validation import DataValidator
from alphascope.feature_store.feature_store import FeatureStore
from alphascope.models.model_registry_store import ModelRegistryStore
from alphascope.marketplace.strategy_marketplace import StrategyMarketplace
from alphascope.monitoring.risk_monitor import RiskMonitor
from alphascope.optimization.bayesian_optimizer import BayesianOptimizer
from alphascope.research.experiment_tracker import ExperimentTracker
from alphascope.sandbox.research_sandbox import ResearchSandbox


def _base_dir() -> Path:
    base_dir = Path("data/processed/test_platform_upgrades")
    if base_dir.exists():
        shutil.rmtree(base_dir)
    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir


def test_dataset_versioning_validation_and_catalog() -> None:
    base_dir = _base_dir()
    dataset = pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-01", periods=5, freq="h"),
            "symbol": ["BTCUSDT"] * 5,
            "close": [100.0, 101.0, 102.0, 103.0, 104.0],
            "volume": [1000, 1100, 1050, 1200, 1300],
        }
    )
    manager = DatasetVersionManager(output_dir=str(base_dir / "datasets"))
    payload = manager.register(dataset, "sample_dataset", ["close", "volume"], {"start": "2024-01-01", "end": "2024-01-02"})
    validation = DataValidator().validate(dataset, expected_schema={"close": "float64"})
    catalog = DataCatalog(base_dir=str(base_dir)).list_datasets()

    assert len(payload["dataset_hash"]) == 64
    assert validation["rows"] == 5
    assert not catalog.empty


def test_feature_store_model_registry_experiment_and_lineage() -> None:
    base_dir = _base_dir()
    store = FeatureStore(output_dir=str(base_dir / "feature_store"))
    try:
        store.store_features(
            symbol="BTCUSDT",
            timestamp=pd.Timestamp("2024-01-01T00:00:00Z").to_pydatetime(),
            features={"RSI": 55.0, "MACD": 1.2},
            feature_version="v2",
            dataset_hash="abc123",
        )
        metadata = store.feature_metadata()
        versions = store.feature_versions()
    finally:
        store.close()

    model_registry = ModelRegistryStore(output_dir=str(base_dir / "models"))
    model_registry.register(
        model_name="gradient_boosting",
        model_version="v3",
        hyperparameters={"max_depth": 3},
        dataset_hash="abc123",
        metrics={"f1": 0.66},
    )
    experiment = ExperimentTracker(output_dir=str(base_dir / "experiments")).track(
        strategy_id="strategy_001",
        feature_set=["RSI", "MACD"],
        target_definition={"future_horizon": 4},
        metrics={"sharpe": 1.2},
        dataset_hash="abc123",
        model_name="gradient_boosting",
        backtest_summary={"total_return": 0.12},
    )
    lineage = DataLineageTracker(output_dir=str(base_dir / "lineage")).record(
        dataset_hash="abc123",
        features_used=["RSI", "MACD"],
        model_version="gradient_boosting_v3",
        strategy_id="strategy_001",
    )

    assert not metadata.empty
    assert not versions.empty
    assert not model_registry.load().empty
    assert experiment["dataset_hash"] == "abc123"
    assert lineage["strategy_id"] == "strategy_001"


def test_benchmark_optimizer_sandbox_marketplace_and_risk_monitor() -> None:
    base_dir = _base_dir()
    benchmark_input = pd.DataFrame(
        [
            {"strategy_id": "s1", "robustness_score": 20.0, "rolling_sharpe": 1.0},
            {"strategy_id": "s2", "robustness_score": 10.0, "rolling_sharpe": 0.5},
        ]
    )
    benchmark = BenchmarkSystem(output_dir=str(base_dir / "benchmarks")).compare(
        benchmark_input,
        ["robustness_score", "rolling_sharpe"],
    )
    optimizer = BayesianOptimizer(seed=42).optimize(
        objective=lambda params: -(params["x"] - 0.7) ** 2 + 1.0,
        search_space={"x": (0.0, 1.0)},
        n_trials=5,
    )
    sandbox = ResearchSandbox(output_dir=str(base_dir / "sandbox")).create_session(
        "quick_signal_test",
        {"dataset": "sample", "features": ["RSI"]},
    )
    marketplace = StrategyMarketplace(output_dir=str(base_dir / "marketplace")).build_listing(
        registry=pd.DataFrame([{"strategy_id": "s1", "status": "candidate"}]),
        health=pd.DataFrame([{"strategy_id": "s1", "robustness_score": 21.0, "rolling_sharpe": 1.1, "degradation_level": "none"}]),
    )
    risk = RiskMonitor().evaluate(
        portfolio_snapshot={"total_equity": 10000.0, "available_capital": 2000.0, "portfolio_return": -0.05},
        positions=pd.DataFrame(
            [
                {"allocation_amount": 5000.0, "unrealized_pnl": 100.0},
                {"allocation_amount": 3000.0, "unrealized_pnl": -50.0},
            ]
        ),
    )

    assert not benchmark.empty
    assert optimizer["best_score"] > 0.0
    assert Path(sandbox["path"]).exists()
    assert not marketplace.empty
    assert "alerts" in risk
