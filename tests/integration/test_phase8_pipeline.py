from __future__ import annotations

import shutil
from pathlib import Path

import pandas as pd

from alphascope.research.research_pipeline import ResearchPipeline


def _dataset_path() -> Path:
    base_dir = Path("data/processed/test_phase8_pipeline")
    if base_dir.exists():
        shutil.rmtree(base_dir)
    base_dir.mkdir(parents=True, exist_ok=True)

    timestamps = pd.date_range("2024-02-01", periods=96, freq="h")
    rows: list[dict[str, object]] = []
    for symbol, bias in [("BTCUSDT", 0.009), ("ETHUSDT", 0.007), ("FETUSDT", 0.013), ("ARBUSDT", 0.006)]:
        close = 100.0
        for index, timestamp in enumerate(timestamps):
            delta = bias if index % 4 != 0 else -0.005
            if symbol == "FETUSDT" and index in (20, 21):
                delta = 0.12
            close *= 1.0 + delta
            rows.append(
                {
                    "timestamp": timestamp,
                    "symbol": symbol,
                    "open": close,
                    "high": close * 1.01,
                    "low": close * 0.99,
                    "close": close,
                    "volume": 500 + index * 15,
                    "rsi": 30 if index % 12 == 0 else 55,
                    "macd": delta,
                    "macd_signal": delta / 2,
                    "bb_upper": close * 1.02,
                    "bb_lower": close * 0.98,
                    "sma_20": close * 0.995,
                    "sma_50": close * 0.99,
                    "pct_return": delta,
                    "volatility": abs(delta),
                    "relative_volume": 1.3 if index % 9 == 0 else 1.0,
                    "sentiment_score": 0.22 if index % 10 == 0 else 0.03,
                    "news_count_window": 2 if index % 10 == 0 else 1,
                    "avg_sentiment_window": 0.18 if index % 10 == 0 else 0.02,
                }
            )
    dataset_path = base_dir / "dataset.csv"
    pd.DataFrame(rows).to_csv(dataset_path, index=False)
    return dataset_path


def test_phase8_research_pipeline_runs_end_to_end() -> None:
    dataset_path = _dataset_path()
    base_dir = dataset_path.parent
    pipeline = ResearchPipeline(
        dataset_path=str(dataset_path),
        research_dir=str(base_dir / "research"),
        discovery_dir=str(base_dir / "discovery"),
        experiments_dir=str(base_dir / "experiments"),
        reports_dir=str(base_dir / "reports"),
    )
    result = pipeline.run()

    assert result["summary"]["regimes_rows"] > 0
    assert result["summary"]["signals_rows"] > 0
    assert result["summary"]["strategies_rows"] > 0
    assert result["summary"]["ranking_rows"] > 0
    assert (base_dir / "discovery" / "regimes_detected.csv").exists()
    assert (base_dir / "discovery" / "discovery_rankings.csv").exists()
    assert (base_dir / "reports" / "alpha_discovery_report.txt").exists()
