from __future__ import annotations

import logging
import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from alphascope.alerts.notifier import AlertNotifier
from alphascope.config.settings import settings
from alphascope.events.event_bus import EventBus
from alphascope.events.producers.pipeline_producer import PipelineEventProducer
from alphascope.feature_store.feature_store import FeatureStore
from alphascope.infrastructure.repositories.model import ModelRunRepository
from alphascope.infrastructure.repositories.prediction import PredictionRepository
from alphascope.models.dataset import Phase3DatasetBuilder
from alphascope.models.predict import load_model_artifact, predict_from_dataframe
from alphascope.models.ranking import build_asset_ranking
from alphascope.monitoring.metrics import MetricsCollector
from alphascope.monitoring.system_status import configure_phase4_logging
from alphascope.monitoring.tracing import JsonTracer
from alphascope.storage.database import StorageSessionLocal
from alphascope.storage.migrations.manager import MigrationManager
from alphascope.storage.models.production import (
    AssetRankingRecord,
    ModelPredictionRecord,
    PortfolioPositionRecord,
    PortfolioSnapshotRecord,
    TradeHistoryRecord,
)
from alphascope.trading.portfolio import Portfolio
from alphascope.trading.execution_engine import ExecutionEngine
from alphascope.trading.paper_broker import PaperBroker
from alphascope.domain.trading_schemas import RiskConfig
from alphascope.utils.time import ensure_utc

logger = logging.getLogger("alphascope.system")


class AutomationPipeline:
    def __init__(
        self,
        dataset_path: str = "data/processed/dataset.csv",
        prediction_repo: PredictionRepository | None = None,
        broker: PaperBroker | None = None,
        notifier: AlertNotifier | None = None,
        event_bus: EventBus | None = None,
        metrics: MetricsCollector | None = None,
        tracer: JsonTracer | None = None,
    ):
        configure_phase4_logging()
        self.dataset_path = dataset_path
        self.state_path = Path("data/processed/system/pipeline_state.json")
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        MigrationManager().upgrade()
        self.prediction_repo = prediction_repo or PredictionRepository()
        self.notifier = notifier or AlertNotifier()
        self.event_bus = event_bus or EventBus()
        self.events = PipelineEventProducer(self.event_bus)
        self.metrics = metrics or MetricsCollector()
        self.tracer = tracer or JsonTracer(service="alphascope-pipeline")
        self.feature_store = FeatureStore()
        self.broker = broker or PaperBroker(
            portfolio=Portfolio(initial_cash=settings.PAPER_TRADING_CAPITAL),
            risk_config=RiskConfig(
                max_risk_per_trade=settings.MAX_RISK_PER_TRADE,
                max_open_positions=settings.MAX_OPEN_POSITIONS,
                stop_loss_pct=settings.STOP_LOSS_PCT,
                take_profit_pct=settings.TAKE_PROFIT_PCT,
            ),
            fee_rate=settings.EXCHANGE_FEE_RATE,
            slippage_rate=settings.SLIPPAGE_RATE,
        )
        self.execution_engine = ExecutionEngine(self.broker)

    def run_once(self) -> dict[str, Any]:
        logger.info("Starting automation pipeline run")
        started_at = time.perf_counter()
        self._write_state({"status": "running", "started_at": datetime.now(UTC).isoformat()})
        self.tracer.record("pipeline_run", "started")
        try:
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
                "predictions_rows": len(predictions),
                "ranking_rows": len(ranking),
                "opened_trades": len(trading_result["opened"]),
                "closed_trades": len(trading_result["closed"]),
                "alerts": len(alerts),
            }
            self.metrics.emit("pipeline_duration", time.perf_counter() - started_at)
            self.metrics.emit("number_of_signals", len(predictions))
            self.metrics.emit(
                "number_of_trades",
                len(trading_result["opened"]) + len(trading_result["closed"]),
            )
            self._write_state(
                {
                    "status": "idle",
                    "last_run_at": datetime.now(UTC).isoformat(),
                    "last_result": result,
                }
            )
            self.tracer.record("pipeline_run", "completed", **result)
            logger.info("Automation pipeline completed successfully: %s", result)
            return result
        except Exception as exc:
            logger.exception("Automation pipeline failed")
            self.metrics.emit("system_errors", 1.0, {"source": "pipeline"})
            self._write_state(
                {
                    "status": "error",
                    "last_error_at": datetime.now(UTC).isoformat(),
                    "last_error": str(exc),
                }
            )
            self.tracer.record("pipeline_run", "error", error=str(exc))
            self.notifier.system_error({"error": str(exc)})
            raise

    def ingest_market_data(self) -> int:
        from alphascope.infrastructure.db.session import SessionLocal
        from alphascope.ingestion.market_ingestor import MarketIngestor

        symbols = self._market_symbols()
        db = SessionLocal()
        ingestor = MarketIngestor()
        ingested = 0
        try:
            for symbol in symbols:
                ingestor.ingest_candles(symbol, settings.DEFAULT_TIMEFRAME, settings.AUTOMATION_MARKET_LIMIT, db)
                ingested += 1
        finally:
            db.close()
        self.events.market_data_updated({"symbols": ingested, "timeframe": settings.DEFAULT_TIMEFRAME})
        self.tracer.record("market_ingestion", "completed", symbols=ingested)
        logger.info("Market ingestion executed for %s symbols", ingested)
        return ingested

    def ingest_news(self) -> int:
        from alphascope.infrastructure.db.session import SessionLocal
        from alphascope.ingestion.news_ingestor import NewsIngestor

        db = SessionLocal()
        try:
            ingested = NewsIngestor().ingest_news(settings.AUTOMATION_NEWS_QUERY, db, days_back=settings.AUTOMATION_NEWS_DAYS)
        finally:
            db.close()
        self.tracer.record("news_ingestion", "completed", news_items=ingested)
        logger.info("News ingestion executed with %s new items", ingested)
        return ingested

    def build_features(self) -> int:
        from alphascope.features.technical import TechnicalFeatures
        from alphascope.infrastructure.db.session import SessionLocal
        from alphascope.infrastructure.repositories.market import MarketRepository
        from alphascope.infrastructure.repositories.technical import TechnicalRepository

        db = SessionLocal()
        market_repo = MarketRepository(db)
        tech_repo = TechnicalRepository(db)
        assets = market_repo.get_assets()
        processed = 0
        try:
            for asset in assets:
                candles_df = market_repo.get_candles_as_df(asset.id, limit=settings.AUTOMATION_MARKET_LIMIT)
                if candles_df.empty:
                    continue
                features_df = TechnicalFeatures.calculate_all(candles_df)
                tech_repo.save_features(features_df, asset.id)
                self._store_latest_feature_snapshot(asset.symbol, features_df)
                processed += 1
        finally:
            db.close()
        self.events.features_computed({"assets": processed})
        self.tracer.record("feature_update", "completed", assets=processed)
        logger.info("Feature update executed for %s assets", processed)
        return processed

    def build_dataset(self) -> str:
        from alphascope.features.pipeline import FeaturePipeline
        from alphascope.infrastructure.db.session import SessionLocal
        from alphascope.infrastructure.repositories.market import MarketRepository
        from alphascope.infrastructure.repositories.sentiment import SentimentRepository
        from alphascope.infrastructure.repositories.technical import TechnicalRepository

        db = SessionLocal()
        market_repo = MarketRepository(db)
        tech_repo = TechnicalRepository(db)
        sentiment_repo = SentimentRepository(db)
        all_frames = []
        try:
            for asset in market_repo.get_assets():
                candles_df = market_repo.get_candles_as_df(asset.id)
                features_df = tech_repo.get_features_as_df(asset.id)
                if candles_df.empty or features_df.empty:
                    continue
                sentiments_df = sentiment_repo.get_all_sentiments_as_df()
                unified_df = FeaturePipeline.consolidate_dataset(candles_df, features_df, sentiments_df)
                unified_df["symbol"] = asset.symbol
                all_frames.append(unified_df)
        finally:
            db.close()

        output_path = Path(self.dataset_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if all_frames:
            pd.concat(all_frames).to_csv(output_path, index=False)
        elif not output_path.exists():
            pd.DataFrame().to_csv(output_path, index=False)
        self.tracer.record("dataset_build", "completed", output_path=str(output_path))
        logger.info("Dataset updated at %s", output_path)
        return str(output_path)

    def predict_assets(self, dataset_path: str | None = None) -> pd.DataFrame:
        artifact = self._load_latest_artifact()
        builder = Phase3DatasetBuilder(feature_columns=artifact["feature_columns"])
        dataset = builder.load_dataset(dataset_path or self.dataset_path)
        prepared = builder.prepare_dataset(dataset, interval=settings.DEFAULT_TIMEFRAME)
        predictions = predict_from_dataframe(artifact, prepared, latest_only=True)
        self.prediction_repo.save_predictions(predictions, f"predictions_{settings.DEFAULT_TIMEFRAME}_auto")
        self._persist_predictions(predictions)
        self.events.model_prediction_ready({"rows": len(predictions)})
        self.metrics.emit("model_inference_latency", float(len(predictions)), {"mode": "batch"})
        self.tracer.record("model_prediction", "completed", rows=len(predictions))
        logger.info("Generated %s asset predictions", len(predictions))
        return predictions

    def rank_assets(self, predictions_df: pd.DataFrame | None = None) -> pd.DataFrame:
        if predictions_df is None:
            predictions_df = self.predict_assets()
        ranking = build_asset_ranking(predictions_df)
        self.prediction_repo.save_ranking(ranking, f"ranking_{settings.DEFAULT_TIMEFRAME}_auto")
        self._persist_ranking(ranking)
        self.events.ranking_updated({"rows": len(ranking)})
        self.tracer.record("ranking_update", "completed", rows=len(ranking))
        logger.info("Generated ranking with %s rows", len(ranking))
        return ranking

    def execute_paper_trading(self, predictions_df: pd.DataFrame | None = None) -> dict[str, list[dict]]:
        if predictions_df is None:
            predictions_df = self.predict_assets()
        result = self.execution_engine.process_predictions(predictions_df)
        self._persist_trading_state(result)
        self.events.trade_executed({"opened": len(result["opened"]), "closed": len(result["closed"])})
        self.events.portfolio_updated(self.broker.portfolio.snapshot().to_dict())
        self.metrics.emit(
            "portfolio_value",
            float(self.broker.portfolio.get_portfolio_value()),
            {"mode": "paper"},
        )
        self.tracer.record(
            "paper_trading",
            "completed",
            opened=len(result["opened"]),
            closed=len(result["closed"]),
        )
        logger.info("Paper trading cycle finished: %s opened, %s closed", len(result["opened"]), len(result["closed"]))
        return result

    def generate_alerts(self, predictions_df: pd.DataFrame, trading_result: dict[str, list[dict]]) -> list[dict[str, Any]]:
        alerts: list[dict[str, Any]] = []
        for _, row in predictions_df.iterrows():
            payload = {
                "Symbol": row["symbol"],
                "Probability": round(float(row["predicted_probability"]), 4),
                "Signal": "STRONG BUY" if float(row["predicted_probability"]) >= 0.75 else "STRONG SELL" if float(row["predicted_probability"]) <= 0.35 else "NEUTRAL",
                "Sentiment": round(float(row.get("sentiment_score", 0.0)), 4),
                "Volatility": round(float(row.get("volatility", 0.0)), 4),
            }
            if float(row["predicted_probability"]) >= 0.75:
                alerts.append(self.notifier.strong_signal(payload, "BUY"))
            elif float(row["predicted_probability"]) <= 0.35:
                alerts.append(self.notifier.strong_signal(payload, "SELL"))

        for trade in trading_result["opened"]:
            alerts.append(self.notifier.trade_executed(trade))
        for trade in trading_result["closed"]:
            alerts.append(self.notifier.trade_closed(trade))
        logger.info("Generated %s alerts", len(alerts))
        return alerts

    def _load_latest_artifact(self) -> dict[str, Any]:
        runs = ModelRunRepository().list_runs()
        if runs.empty:
            raise FileNotFoundError("No trained model artifact found for automation.")
        path = str(runs.sort_values("created_at").iloc[-1]["artifact_path"])
        return load_model_artifact(path)

    def _market_symbols(self) -> list[str]:
        raw_symbols = [item.strip() for item in settings.AUTOMATION_MARKET_SYMBOLS.split(",") if item.strip()]
        return [self._exchange_symbol(symbol) for symbol in raw_symbols]

    @staticmethod
    def _exchange_symbol(symbol: str) -> str:
        if "/" in symbol:
            return symbol
        if symbol.endswith("USDT"):
            return f"{symbol[:-4]}/USDT"
        return symbol

    def _write_state(self, payload: dict[str, Any]) -> None:
        current: dict[str, Any] = {}
        if self.state_path.exists():
            current = json.loads(self.state_path.read_text(encoding="utf-8"))
        current.update(payload)
        self.state_path.write_text(json.dumps(current, indent=2, default=str), encoding="utf-8")

    def _store_latest_feature_snapshot(self, symbol: str, features_df: pd.DataFrame) -> None:
        if features_df.empty:
            return
        latest = features_df.sort_values("timestamp").iloc[-1].to_dict()
        feature_payload = {
            key: value
            for key, value in latest.items()
            if key != "timestamp" and isinstance(value, (int, float))
        }
        if feature_payload:
            self.feature_store.store_features(
                symbol=symbol,
                timestamp=ensure_utc(latest["timestamp"]) or pd.to_datetime(latest["timestamp"], utc=True).to_pydatetime(),
                features=feature_payload,
            )

    def _persist_predictions(self, predictions: pd.DataFrame) -> None:
        session = StorageSessionLocal()
        try:
            for row in predictions.to_dict(orient="records"):
                session.add(
                    ModelPredictionRecord(
                        symbol=row.get("symbol", "UNKNOWN"),
                        interval=row.get("interval", settings.DEFAULT_TIMEFRAME),
                        predicted_label=int(row.get("predicted_label", 0)),
                        predicted_probability=float(row.get("predicted_probability", 0.0)),
                        confidence_score=float(row.get("confidence_score", row.get("predicted_probability", 0.0))),
                        model_name=row.get("model_name", "auto"),
                    )
                )
            session.commit()
        finally:
            session.close()

    def _persist_ranking(self, ranking: pd.DataFrame) -> None:
        session = StorageSessionLocal()
        try:
            for row in ranking.to_dict(orient="records"):
                session.add(
                    AssetRankingRecord(
                        symbol=row.get("symbol", "UNKNOWN"),
                        interval=row.get("interval", settings.DEFAULT_TIMEFRAME),
                        predicted_probability=float(row.get("predicted_probability", 0.0)),
                        opportunity_score=float(row.get("opportunity_score", 0.0)),
                        risk_score=float(row.get("risk_score", 0.0)),
                        final_score=float(row.get("final_score", 0.0)),
                    )
                )
            session.commit()
        finally:
            session.close()

    def _persist_trading_state(self, result: dict[str, list[dict]]) -> None:
        session = StorageSessionLocal()
        try:
            portfolio_snapshot = self.broker.portfolio.snapshot().to_dict()
            session.add(
                PortfolioSnapshotRecord(
                    total_equity=float(portfolio_snapshot.get("equity", 0.0)),
                    available_capital=float(portfolio_snapshot.get("cash_balance", 0.0)),
                    portfolio_value=float(portfolio_snapshot.get("equity", 0.0)),
                    portfolio_return=float(
                        (portfolio_snapshot.get("equity", 0.0) - self.broker.portfolio.initial_cash)
                        / self.broker.portfolio.initial_cash
                    ) if self.broker.portfolio.initial_cash else 0.0,
                )
            )
            session.query(PortfolioPositionRecord).delete(synchronize_session=False)
            for symbol, position in self.broker.portfolio.positions.items():
                session.add(
                    PortfolioPositionRecord(
                        symbol=symbol,
                        quantity=float(position.quantity),
                        entry_price=float(position.entry_price),
                        current_price=float(position.entry_price),
                        unrealized_pnl=0.0,
                        allocation_amount=float(position.quantity * position.entry_price),
                    )
                )
            for trade in result["opened"] + result["closed"]:
                trade_id = str(trade.get("trade_id", ""))
                exists = session.query(TradeHistoryRecord).filter(TradeHistoryRecord.trade_id == trade_id).first()
                if exists:
                    continue
                session.add(
                    TradeHistoryRecord(
                        trade_id=trade_id,
                        symbol=str(trade.get("symbol", "UNKNOWN")),
                        side=str(trade.get("side", "BUY")),
                        entry_price=float(trade.get("entry_price", 0.0)),
                        exit_price=float(trade.get("exit_price", 0.0)) if trade.get("exit_price") is not None else None,
                        quantity=float(trade.get("quantity", 0.0)),
                        pnl=float(trade.get("pnl", 0.0)),
                        status=str(trade.get("status", "OPEN")),
                    )
                )
            session.commit()
        finally:
            session.close()
