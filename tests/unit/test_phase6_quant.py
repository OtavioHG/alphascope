from __future__ import annotations

import shutil
from pathlib import Path

import pandas as pd

from alphascope.optimization.strategy_optimizer import StrategyOptimizer
from alphascope.optimization.walk_forward import WalkForwardValidator
from alphascope.portfolio.allocation import AllocationEngine, equal_weight_allocation, kelly_fraction_allocation, risk_parity_allocation
from alphascope.portfolio.portfolio_engine import MultiAssetPortfolioEngine
from alphascope.portfolio.risk_management import PortfolioRiskConfig, RiskManager


def _dataset_path() -> Path:
    base_dir = Path("data/processed/test_phase6_quant")
    if base_dir.exists():
        shutil.rmtree(base_dir)
    base_dir.mkdir(parents=True, exist_ok=True)

    timestamps = pd.date_range("2024-01-01", periods=120, freq="h")
    rows = []
    for symbol, bias in (("BTCUSDT", 0.02), ("ETHUSDT", 0.01)):
        close = 100.0
        for index, timestamp in enumerate(timestamps):
            delta = bias if index % 2 == 0 else -0.01
            close *= 1.0 + delta
            rows.append(
                {
                    "timestamp": timestamp,
                    "symbol": symbol,
                    "open": close,
                    "high": close * 1.01,
                    "low": close * 0.99,
                    "close": close,
                    "volume": 100 + index,
                    "rsi": 45 + (index % 10),
                    "macd": delta,
                    "macd_signal": delta / 2,
                    "bb_upper": close * 1.02,
                    "bb_lower": close * 0.98,
                    "sma_20": close * 0.99,
                    "sma_50": close * 0.98,
                    "pct_return": delta,
                    "volatility": abs(delta),
                    "relative_volume": 1.0 + ((index % 4) / 10),
                    "sentiment_score": 0.2 if delta > 0 else -0.1,
                    "news_count_window": index % 3,
                    "avg_sentiment_window": 0.2 if delta > 0 else -0.1,
                    "top_topic": "btc" if symbol == "BTCUSDT" else "eth",
                }
            )
    dataset_path = base_dir / "dataset.csv"
    pd.DataFrame(rows).to_csv(dataset_path, index=False)
    return dataset_path


def test_allocation_methods_return_expected_shapes() -> None:
    assert equal_weight_allocation(["BTC", "ETH"], 1000.0) == {"BTC": 500.0, "ETH": 500.0}
    risk_alloc = risk_parity_allocation({"BTC": 0.02, "ETH": 0.04}, 1000.0)
    assert round(sum(risk_alloc.values()), 6) == 1000.0
    kelly_alloc = kelly_fraction_allocation({"BTC": 0.7}, {"BTC": 1.5}, 1000.0)
    assert 0.0 <= kelly_alloc["BTC"] <= 250.0


def test_risk_manager_and_portfolio_engine_respect_limits() -> None:
    risk_manager = RiskManager(PortfolioRiskConfig(max_risk_per_trade=0.2, max_portfolio_exposure=0.5, max_open_positions=2))
    approved, reason = risk_manager.validate_new_position(100.0, 1000.0, 0.1, 0)
    assert approved is True
    assert reason == "approved"

    engine = MultiAssetPortfolioEngine(initial_equity=1000.0, allocation_engine=AllocationEngine("equal_weight"), risk_manager=risk_manager)
    engine.open_position("BTCUSDT", price=100.0, allocation_amount=100.0)
    snapshot = engine.snapshot({"BTCUSDT": 105.0})
    assert snapshot["open_positions"] == 1
    assert snapshot["portfolio_value"] > 0


def test_walk_forward_validation_runs() -> None:
    dataset_path = _dataset_path()
    result = WalkForwardValidator(output_dir="data/processed/test_phase6_quant/optimization").run(
        dataset_path=str(dataset_path),
        train_size=80,
        test_size=20,
        step_size=20,
        horizon=1,
        threshold=0.005,
    )

    assert not result["results"].empty
    assert result["path"].exists()


def test_strategy_optimizer_generates_results() -> None:
    dataset_path = _dataset_path()
    result = StrategyOptimizer(output_dir="data/processed/test_phase6_quant/optimization").optimize(
        dataset_path=str(dataset_path),
        symbol="BTCUSDT",
        horizon_values=[1],
        threshold_values=[0.005],
        buy_thresholds=[0.6],
        sell_thresholds=[0.4],
        method="grid",
    )

    assert not result["results"].empty
    assert result["path"].exists()
    assert "sharpe_ratio" in result["results"].columns
