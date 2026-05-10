from __future__ import annotations

import json
import shutil
from pathlib import Path

import pandas as pd

from alphascope.dashboard.components.charts import equity_curve
from alphascope.dashboard.services.data_service import DashboardDataService
from alphascope.dashboard.services.ranking_service import RankingService
from alphascope.dashboard.services.trading_service import TradingService


def _prepare_base() -> Path:
    base_dir = Path("data/processed/test_phase5_services")
    if base_dir.exists():
        shutil.rmtree(base_dir)
    (base_dir / "rankings").mkdir(parents=True, exist_ok=True)
    (base_dir / "predictions").mkdir(parents=True, exist_ok=True)
    (base_dir / "paper_trades").mkdir(parents=True, exist_ok=True)
    (base_dir / "backtests").mkdir(parents=True, exist_ok=True)
    (base_dir / "logs").mkdir(parents=True, exist_ok=True)
    return base_dir


def test_data_service_loads_dataset_and_logs() -> None:
    base_dir = _prepare_base()
    dataset_path = base_dir / "dataset.csv"
    dataset = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(["2024-01-01 00:00:00", "2024-01-01 01:00:00"]),
            "symbol": ["BTCUSDT", "ETHUSDT"],
            "close": [100.0, 50.0],
            "sentiment_score": [0.2, -0.1],
        }
    )
    dataset.to_csv(dataset_path, index=False)
    (base_dir / "logs" / "system.log").write_text("line1\nline2\n", encoding="utf-8")

    service = DashboardDataService(dataset_path=dataset_path, logs_dir=base_dir / "logs")
    loaded = service.load_dataset()

    assert len(loaded) == 2
    assert service.get_available_symbols() == ["BTCUSDT", "ETHUSDT"]
    assert service.load_recent_logs("system.log", lines=1) == ["line2"]


def test_ranking_service_enriches_ranking_with_predictions() -> None:
    base_dir = _prepare_base()
    pd.DataFrame(
        {
            "symbol": ["BTCUSDT", "ETHUSDT"],
            "score_high": [0.8, 0.6],
            "score_risk": [0.2, 0.3],
            "score_final": [0.64, 0.42],
            "timestamp": pd.to_datetime(["2024-01-01 00:00:00", "2024-01-01 00:00:00"]),
        }
    ).to_csv(base_dir / "rankings" / "ranking_1h_auto.csv", index=False)

    pd.DataFrame(
        {
            "symbol": ["BTCUSDT", "ETHUSDT"],
            "predicted_probability": [0.81, 0.55],
            "confidence_score": [0.62, 0.10],
            "sentiment_score": [0.3, -0.2],
        }
    ).to_csv(base_dir / "predictions" / "predictions_1h_auto.csv", index=False)

    service = RankingService(
        rankings_dir=base_dir / "rankings",
        predictions_dir=base_dir / "predictions",
        dataset_path=base_dir / "dataset.csv",
    )
    ranking = service.load_latest_ranking()

    assert "predicted_probability" in ranking.columns
    assert "sentiment_score" in ranking.columns
    assert ranking.iloc[0]["symbol"] == "BTCUSDT"


def test_trading_service_calculates_metrics_and_curve() -> None:
    base_dir = _prepare_base()
    trades = pd.DataFrame(
        {
            "trade_id": ["1", "2"],
            "symbol": ["BTCUSDT", "ETHUSDT"],
            "entry_price": [100.0, 50.0],
            "exit_price": [110.0, 45.0],
            "quantity": [1.0, 2.0],
            "pnl": [10.0, -10.0],
            "status": ["CLOSED", "CLOSED"],
            "timestamp": pd.to_datetime(["2024-01-01 01:00:00", "2024-01-01 02:00:00"]),
        }
    )
    trades.to_csv(base_dir / "paper_trades" / "trades.csv", index=False)
    (base_dir / "paper_trades" / "portfolio_snapshot.json").write_text(
        json.dumps({"cash_balance": 9000.0, "equity": 10050.0, "open_positions": 1}),
        encoding="utf-8",
    )
    pd.DataFrame(
        {
            "timestamp": pd.to_datetime(["2024-01-01 00:00:00", "2024-01-01 01:00:00"]),
            "equity": [10000.0, 10050.0],
        }
    ).to_csv(base_dir / "backtests" / "backtest_equity_curve.csv", index=False)

    service = TradingService(
        trades_dir=base_dir / "paper_trades",
        backtests_dir=base_dir / "backtests",
    )
    metrics = service.calculate_metrics()
    curve = service.load_equity_curve()

    assert metrics["closed_trades"] == 2
    assert metrics["realized_pnl"] == 0.0
    assert metrics["equity"] == 10050.0
    assert len(curve) == 2


def test_equity_curve_accepts_live_total_equity_column() -> None:
    curve = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(["2024-01-01 00:00:00", "2024-01-01 01:00:00"], utc=True),
            "total_equity": [10000.0, 10075.0],
        }
    )

    figure = equity_curve(curve)

    assert figure is not None
