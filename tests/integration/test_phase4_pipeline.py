from __future__ import annotations

import shutil
from pathlib import Path

import pandas as pd

from alphascope.alerts.notifier import AlertNotifier
from alphascope.automation.pipeline import AutomationPipeline
from alphascope.infrastructure.repositories.portfolio_repository import PortfolioRepository
from alphascope.infrastructure.repositories.prediction import PredictionRepository
from alphascope.infrastructure.repositories.trade_repository import TradeRepository
from alphascope.trading.paper_broker import PaperBroker
from alphascope.trading.portfolio import Portfolio
from alphascope.domain.trading_schemas import RiskConfig


class DummyNotifier(AlertNotifier):
    def __init__(self, alerts_dir: str):
        super().__init__(alerts_dir=alerts_dir)
        self.sent: list[dict] = []

    def send_alert(self, alert_type: str, title: str, payload: dict):
        record = super().send_alert(alert_type, title, payload)
        self.sent.append(record)
        return record


class DummyAutomationPipeline(AutomationPipeline):
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        broker = PaperBroker(
            portfolio=Portfolio(initial_cash=5000.0),
            trade_repository=TradeRepository(base_dir / "paper_trades"),
            portfolio_repository=PortfolioRepository(base_dir / "paper_trades"),
            risk_config=RiskConfig(max_risk_per_trade=0.1, max_open_positions=3, stop_loss_pct=0.05),
            fee_rate=0.0,
            slippage_rate=0.0,
        )
        super().__init__(
            dataset_path=str(base_dir / "dataset.csv"),
            prediction_repo=PredictionRepository(base_dir / "predictions"),
            broker=broker,
            notifier=DummyNotifier(str(base_dir / "alerts")),
        )

    def ingest_market_data(self) -> int:
        return 1

    def ingest_news(self) -> int:
        return 1

    def build_features(self) -> int:
        return 1

    def build_dataset(self) -> str:
        dataset = pd.DataFrame(
            {
                "timestamp": pd.to_datetime(["2024-01-01 00:00:00", "2024-01-01 00:00:00"]),
                "symbol": ["BTCUSDT", "ETHUSDT"],
                "close": [100.0, 50.0],
                "predicted_probability": [0.82, 0.25],
                "sentiment_score": [0.4, -0.2],
                "volatility": [0.02, 0.05],
                "relative_volume": [1.5, 0.9],
            }
        )
        dataset.to_csv(self.dataset_path, index=False)
        return self.dataset_path

    def predict_assets(self, dataset_path: str | None = None) -> pd.DataFrame:
        predictions = pd.read_csv(dataset_path or self.dataset_path)
        predictions["timestamp"] = pd.to_datetime(predictions["timestamp"])
        predictions["predicted_label"] = (predictions["predicted_probability"] >= 0.5).astype(int)
        predictions["confidence_score"] = abs(predictions["predicted_probability"] - 0.5) * 2.0
        self.prediction_repo.save_predictions(predictions, "predictions_auto_test")
        return predictions


def test_automation_pipeline_runs_end_to_end() -> None:
    base_dir = Path("data/processed/test_phase4_pipeline")
    if base_dir.exists():
        shutil.rmtree(base_dir)
    base_dir.mkdir(parents=True, exist_ok=True)

    pipeline = DummyAutomationPipeline(base_dir)
    result = pipeline.run_once()

    assert result["predictions_rows"] == 2
    assert result["ranking_rows"] == 2
    assert result["opened_trades"] == 1
    assert result["alerts"] >= 2
    assert (base_dir / "predictions" / "predictions_auto_test.csv").exists()
    assert (base_dir / "paper_trades" / "trades.csv").exists()
