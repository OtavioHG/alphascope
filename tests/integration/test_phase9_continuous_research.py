from __future__ import annotations

import shutil
from pathlib import Path

import pandas as pd

from alphascope.research_continuous.continuous_research import ContinuousResearchPipeline


def _dataset_path() -> Path:
    base_dir = Path("data/processed/test_phase9_pipeline")
    if base_dir.exists():
        shutil.rmtree(base_dir)
    base_dir.mkdir(parents=True, exist_ok=True)

    timestamps = pd.date_range("2024-03-01", periods=120, freq="h")
    rows: list[dict[str, object]] = []
    for symbol, bias in [("BTCUSDT", 0.008), ("ETHUSDT", 0.006), ("FETUSDT", 0.014)]:
        close = 100.0
        for index, timestamp in enumerate(timestamps):
            delta = bias if index % 5 else -0.007
            if symbol == "FETUSDT" and index in (40, 41, 42):
                delta = 0.11
            close *= 1.0 + delta
            rows.append(
                {
                    "timestamp": timestamp,
                    "symbol": symbol,
                    "open": close,
                    "high": close * 1.01,
                    "low": close * 0.99,
                    "close": close,
                    "volume": 1000 + index * 10,
                    "rsi": 32 if index % 13 == 0 else 56,
                    "macd": delta,
                    "macd_signal": delta / 2,
                    "bb_upper": close * 1.02,
                    "bb_lower": close * 0.98,
                    "sma_20": close * 0.995,
                    "sma_50": close * 0.99,
                    "pct_return": delta,
                    "volatility": abs(delta),
                    "relative_volume": 1.35 if index % 11 == 0 else 1.0,
                    "sentiment_score": 0.2 if index % 9 == 0 else 0.04,
                    "news_count_window": 2 if index % 9 == 0 else 1,
                    "avg_sentiment_window": 0.16 if index % 9 == 0 else 0.03,
                }
            )
    dataset_path = base_dir / "dataset.csv"
    pd.DataFrame(rows).to_csv(dataset_path, index=False)
    return dataset_path


def test_phase9_continuous_research_runs_end_to_end() -> None:
    dataset_path = _dataset_path()
    base_dir = dataset_path.parent
    pipeline = ContinuousResearchPipeline(
        dataset_path=str(dataset_path),
        evolution_dir=str(base_dir / "evolution"),
        lifecycle_dir=str(base_dir / "lifecycle"),
        governance_dir=str(base_dir / "governance"),
        reports_dir=str(base_dir / "reports"),
    )
    result = pipeline.run()

    assert result["summary"]["health_rows"] > 0
    assert result["summary"]["decision_rows"] > 0
    assert (base_dir / "evolution" / "strategy_health.csv").exists()
    assert (base_dir / "governance" / "promotion_decisions.csv").exists()
    assert (base_dir / "reports" / "strategy_lifecycle_report.txt").exists()
