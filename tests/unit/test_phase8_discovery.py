from __future__ import annotations

import shutil
from pathlib import Path

import pandas as pd

from alphascope.discovery.alpha_ranker import AlphaRanker
from alphascope.discovery.anomaly_detection import AnomalyDetector
from alphascope.discovery.regime_detection import RegimeDetector
from alphascope.discovery.signal_mining import SignalMiner
from alphascope.discovery.strategy_generator import StrategyGenerator
from alphascope.reports.alpha_reports import AlphaReportBuilder
from alphascope.reports.strategy_reports import StrategyReportBuilder
from alphascope.research.experiment_tracker import ExperimentTracker


def _make_dataset() -> pd.DataFrame:
    timestamps = pd.date_range("2024-01-01", periods=72, freq="h")
    rows: list[dict[str, object]] = []
    for symbol, bias in [("BTCUSDT", 0.01), ("ETHUSDT", 0.008), ("FETUSDT", 0.015)]:
        close = 100.0
        for index, timestamp in enumerate(timestamps):
            if symbol == "FETUSDT" and index == 30:
                delta = 0.18
            else:
                delta = bias if index % 3 != 0 else -0.006
            close *= 1.0 + delta
            rows.append(
                {
                    "timestamp": timestamp,
                    "symbol": symbol,
                    "open": close * 0.998,
                    "high": close * 1.01,
                    "low": close * 0.99,
                    "close": close,
                    "volume": 1000 + index * 10,
                    "rsi": 28 if index % 10 == 0 else 55,
                    "macd": delta,
                    "macd_signal": delta / 2,
                    "bb_upper": close * 1.02,
                    "bb_lower": close * 0.98,
                    "sma_20": close * 0.995,
                    "sma_50": close * 0.99,
                    "pct_return": delta,
                    "volatility": abs(delta),
                    "relative_volume": 1.4 if index in (10, 30, 40) else 1.0,
                    "sentiment_score": 0.25 if index % 8 == 0 else 0.05,
                    "news_count_window": 3 if index in (10, 30, 40) else 1,
                    "avg_sentiment_window": 0.2 if index % 8 == 0 else 0.04,
                }
            )
    return pd.DataFrame(rows)


def test_phase8_discovery_components_generate_valid_outputs() -> None:
    dataset = _make_dataset()

    regimes = RegimeDetector().detect(dataset)
    anomalies = AnomalyDetector(rolling_window=8, z_threshold=2.0).detect(dataset)
    signals = SignalMiner(future_horizon=2).mine(dataset)
    strategies = StrategyGenerator().generate(signals, regimes)
    ranking = AlphaRanker().rank(strategies, signals)

    assert not regimes.empty
    assert set(regimes["regime_label"]).intersection({"bullish", "bearish", "sideways", "high_volatility", "low_liquidity", "news_driven"})
    assert not anomalies.empty
    assert (signals["sample_count"] > 0).all()
    assert not strategies.empty
    assert set(strategies["promotion_status"]).issubset({"research_only", "candidate", "promoted"})
    assert not ranking.empty
    assert ranking["alpha_discovery_score"].iloc[0] >= ranking["alpha_discovery_score"].iloc[-1]


def test_phase8_experiment_tracking_and_reports() -> None:
    base_dir = Path("data/processed/test_phase8_unit")
    if base_dir.exists():
        shutil.rmtree(base_dir)
    base_dir.mkdir(parents=True, exist_ok=True)

    tracker = ExperimentTracker(output_dir=str(base_dir / "experiments"))
    tracked = tracker.track(
        strategy_id="strategy_001",
        feature_set=["rsi", "macd"],
        target_definition={"future_horizon": 4, "return_threshold": 0.015},
        metrics={"sharpe": 1.2, "win_rate": 0.65},
        promotion_status="candidate",
    )
    loaded = tracker.load()

    ranked = pd.DataFrame(
        [{"strategy_id": "strategy_001", "alpha_discovery_score": 42.0, "promotion_status": "candidate"}]
    )
    anomalies = pd.DataFrame([{"symbol": "FETUSDT", "anomaly_type": "volume_spike", "anomaly_score": 3.1}])
    hypotheses = pd.DataFrame([{"summary": "AI tokens reagem melhor em lateralizacao do BTC"}])
    alpha_paths = AlphaReportBuilder(output_dir=str(base_dir / "reports")).build(ranked, anomalies, hypotheses)
    strategy_paths = StrategyReportBuilder(output_dir=str(base_dir / "reports")).build(
        pd.DataFrame([{"strategy_id": "strategy_001"}]),
        pd.DataFrame([{"signal_definition": "sma_macd_bullish"}]),
    )

    assert tracked["strategy_id"] == "strategy_001"
    assert not loaded.empty
    assert alpha_paths["text_path"].exists()
    assert strategy_paths["strategies_path"].exists()
