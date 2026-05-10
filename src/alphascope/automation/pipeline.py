from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from alphascope.alerts.notifier import AlertNotifier
from alphascope.infrastructure.repositories.prediction import PredictionRepository
from alphascope.monitoring.metrics import MetricsCollector
from alphascope.trading.execution_engine import ExecutionEngine
from alphascope.trading.paper_broker import PaperBroker


class AutomationPipeline:
    """Compatibility pipeline used by legacy integration tests and basic API runs."""

    def __init__(
        self,
        dataset_path: str = "data/processed/dataset.csv",
        prediction_repo: PredictionRepository | None = None,
        broker: PaperBroker | None = None,
        notifier: AlertNotifier | None = None,
        metrics: MetricsCollector | None = None,
    ) -> None:
        self.dataset_path = str(dataset_path)
        self.state_path = Path("data/processed/system/pipeline_state.json")
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.prediction_repo = prediction_repo or PredictionRepository()
        self.broker = broker or PaperBroker()
        self.notifier = notifier or AlertNotifier()
        self.metrics = metrics or MetricsCollector()
        self.execution_engine = ExecutionEngine(self.broker)

    def run_once(self) -> dict[str, Any]:
        self._write_state({"status": "running", "started_at": datetime.now(UTC).isoformat()})

        self.ingest_market_data()
        self.ingest_news()
        self.build_features()
        dataset_path = self.build_dataset()
        predictions = self.predict_assets(dataset_path=dataset_path)
        ranking = self.rank_assets(predictions)
        trading_result = self.execute_paper_trading(predictions)
        alerts = self.generate_alerts(predictions, trading_result)

        result = {
            "dataset_path": dataset_path,
            "predictions_rows": int(len(predictions)),
            "ranking_rows": int(len(ranking)),
            "opened_trades": int(len(trading_result["opened"])),
            "closed_trades": int(len(trading_result["closed"])),
            "alerts": int(len(alerts)),
        }
        self.metrics.emit("pipeline_runs", 1.0)
        self.metrics.emit("pipeline_predictions", float(len(predictions)))
        self._write_state({"status": "idle", "last_run_at": datetime.now(UTC).isoformat(), "last_result": result})
        return result

    def ingest_market_data(self) -> int:
        return 0

    def ingest_news(self) -> int:
        return 0

    def build_features(self) -> int:
        return 0

    def build_dataset(self) -> str:
        output_path = Path(self.dataset_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if not output_path.exists():
            pd.DataFrame(columns=["timestamp", "symbol", "close", "predicted_probability"]).to_csv(output_path, index=False)
        return str(output_path)

    def predict_assets(self, dataset_path: str | None = None) -> pd.DataFrame:
        path = Path(dataset_path or self.dataset_path)
        if not path.exists():
            return pd.DataFrame(columns=["timestamp", "symbol", "close", "predicted_probability", "predicted_label", "confidence_score"])
        frame = pd.read_csv(path)
        if frame.empty:
            return frame
        if "timestamp" in frame.columns:
            frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True, errors="coerce")
        else:
            frame["timestamp"] = pd.Timestamp.now(tz="UTC")
        if "predicted_probability" not in frame.columns:
            if "score_final" in frame.columns:
                scores = pd.to_numeric(frame["score_final"], errors="coerce").fillna(0.5)
                max_abs = max(float(scores.abs().max()), 1.0)
                frame["predicted_probability"] = ((scores / (2 * max_abs)) + 0.5).clip(0.0, 1.0)
            else:
                frame["predicted_probability"] = 0.5
        frame["predicted_label"] = (pd.to_numeric(frame["predicted_probability"], errors="coerce").fillna(0.0) >= 0.5).astype(int)
        frame["confidence_score"] = (pd.to_numeric(frame["predicted_probability"], errors="coerce").fillna(0.5) - 0.5).abs() * 2.0
        self.prediction_repo.save_predictions(frame, "predictions_auto")
        return frame

    def rank_assets(self, predictions_df: pd.DataFrame) -> pd.DataFrame:
        if predictions_df.empty:
            ranking = pd.DataFrame(columns=["symbol", "score_final"])
        else:
            ranking = predictions_df.sort_values("predicted_probability", ascending=False).copy()
            ranking["score_final"] = pd.to_numeric(ranking["predicted_probability"], errors="coerce").fillna(0.0)
        self.prediction_repo.save_ranking(ranking[[col for col in ranking.columns if col in {"symbol", "score_final", "predicted_probability", "confidence_score"}]] if not ranking.empty else ranking, "ranking_auto")
        return ranking

    def execute_paper_trading(self, predictions_df: pd.DataFrame) -> dict[str, list[dict[str, Any]]]:
        if predictions_df.empty:
            return {"decisions": [], "opened": [], "closed": []}
        return self.execution_engine.process_predictions(predictions_df)

    def generate_alerts(self, predictions_df: pd.DataFrame, trading_result: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
        alerts: list[dict[str, Any]] = []
        for position in trading_result.get("opened", []):
            alerts.append(self.notifier.trade_executed(position))
        for trade in trading_result.get("closed", []):
            alerts.append(self.notifier.trade_closed(trade))
        if not predictions_df.empty:
            top_row = predictions_df.sort_values("predicted_probability", ascending=False).iloc[0]
            alerts.append(
                self.notifier.strong_signal(
                    {
                        "symbol": str(top_row.get("symbol", "UNKNOWN")),
                        "probability": float(top_row.get("predicted_probability", 0.0)),
                    },
                    side="BUY",
                )
            )
        return alerts

    def _write_state(self, payload: dict[str, Any]) -> None:
        self.state_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
