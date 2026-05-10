"""Continuous market/news/ranking pipeline for long-running operation."""

from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from alphascope.alerts import AlertDispatcher
from alphascope.config.settings import settings
from alphascope.core.logger import get_logger
from alphascope.core.pipeline import AlphaScopePipeline
from alphascope.execution import selected_trader_name, should_use_live_trader
from alphascope.datasets.news_dataset_builder import NewsDatasetBuilder
from alphascope.nlp.inference import NewsInferenceEngine
from alphascope.storage.repositories import StorageRepository
from alphascope.utils.time import ensure_utc, safe_utc_diff, utc_now

logger = get_logger(__name__)

_DEFAULT_NEWS_QUERY = "crypto OR bitcoin OR ethereum"


@dataclass(slots=True)
class ContinuousPipelineConfig:
    """Configuration for continuous execution cycles."""

    cycle_interval_seconds: int
    news_refresh_interval_seconds: int
    symbols: list[str]
    timeframe: str
    candle_limit: int
    enable_news: bool = True
    enable_market_refresh: bool = True
    enable_paper_trading: bool = True
    duration_minutes: int | None = None
    run_forever: bool = False
    news_query: str = _DEFAULT_NEWS_QUERY
    news_limit: int = 10
    news_days: int = 1


@dataclass(slots=True)
class ContinuousCycleResult:
    """Summary of a single continuous cycle."""

    cycle_number: int
    started_at: datetime
    finished_at: datetime
    symbols: list[str]
    timeframe: str
    market_rows: int
    feature_rows: int
    ranking_rows: int
    trades_executed: int
    news_rows: int
    snapshot_saved: bool
    success: bool
    error_message: str | None = None

    @property
    def duration_seconds(self) -> float:
        return (self.finished_at - self.started_at).total_seconds()


class ContinuousPipeline:
    """Run the AlphaScope pipeline repeatedly in operational cycles."""

    def __init__(
        self,
        config: ContinuousPipelineConfig,
        *,
        pipeline: AlphaScopePipeline | None = None,
        repository: StorageRepository | None = None,
        news_builder: NewsDatasetBuilder | None = None,
        news_inference: NewsInferenceEngine | None = None,
        state_path: str | Path | None = None,
        alert_dispatcher: AlertDispatcher | None = None,
    ) -> None:
        self.config = config
        self.repository = repository or StorageRepository()
        self.pipeline = pipeline or AlphaScopePipeline(repository=self.repository)
        self.news_builder = news_builder or NewsDatasetBuilder()
        self.news_inference = news_inference or NewsInferenceEngine()
        self.alert_dispatcher = alert_dispatcher or AlertDispatcher()
        self.state_path = Path(state_path) if state_path else Path("data/runtime/continuous_pipeline_status.json")
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self._stop_event = threading.Event()
        self._cycle_count = 0
        self._error_count = 0
        self._last_news_refresh_at: datetime | None = None
        self._last_ranking_at: datetime | None = None
        self._last_snapshot_at: datetime | None = None
        self._write_state({"status": "initialized", "updated_at": self._now_iso()})

    def refresh_market(self) -> list[dict[str, object]]:
        """Refresh market data for the configured symbol universe."""
        return self.pipeline.ingest_market(self.config.symbols, [self.config.timeframe], self.config.candle_limit)

    def refresh_news(self) -> pd.DataFrame:
        """Fetch and score recent news, persisting the latest scored dataset."""
        try:
            dataset = self.news_builder.fetch_gdelt(
                query=self.config.news_query,
                max_records=self.config.news_limit,
                days=self.config.news_days,
            )
        except Exception as e:
            logger.warning(f"News refresh skipped due to external failure: {e}")
            return pd.DataFrame()

        if dataset.empty:
            logger.info("News refresh returned no rows")
            self._last_news_refresh_at = utc_now()
            return dataset
        self.news_builder.save_dataset(dataset, "gdelt_news_latest.csv")
        
        try:
            scored = self.news_inference.score_frame(dataset)
            scored.to_csv(self.repository_path_for_scored_news(), index=False)
            self._last_news_refresh_at = utc_now()
            logger.info("News refresh completed with %s rows", len(scored))
            return scored
        except Exception as e:
            logger.error(f"News scoring failed: {e}")
            return pd.DataFrame()

    def build_features(self) -> pd.DataFrame:
        """Build technical features for the configured symbol universe."""
        return self.pipeline.build_features(self.config.symbols, self.config.timeframe)

    def build_ranking(self) -> pd.DataFrame:
        """Build and persist ranking for the configured symbol universe."""
        ranking = self.pipeline.rank_assets(self.config.symbols, self.config.timeframe)
        self._last_ranking_at = utc_now()
        return ranking

    def run_trading_cycle(self) -> dict[str, object]:
        """Execute one trading cycle from the latest ranking using the selected trader."""
        ranking = self.pipeline.rank_assets(self.config.symbols, self.config.timeframe)
        result = self.pipeline.execute_trading_cycle(
            ranking=ranking,
            symbols=self.config.symbols,
            interval=self.config.timeframe,
        )
        snapshot = result.get("snapshot")
        if isinstance(snapshot, dict) and snapshot.get("timestamp"):
            self._last_snapshot_at = ensure_utc(snapshot["timestamp"])
        else:
            self._last_snapshot_at = utc_now()
        return result

    def run_cycle(self) -> ContinuousCycleResult:
        """Execute a full continuous pipeline cycle."""
        self._validate_config()
        self._cycle_count += 1
        cycle_started_at = utc_now()
        logger.info("Continuous pipeline cycle #%s started", self._cycle_count)
        market_rows = 0
        feature_rows = 0
        ranking_rows = 0
        trades_executed = 0
        news_rows = 0
        snapshot_saved = False

        try:
            if self.config.enable_market_refresh:
                market_result = self.refresh_market()
                market_rows = sum(int(item.get("rows", 0)) for item in market_result)

            if self._should_refresh_news():
                try:
                    news_result = self.refresh_news()
                    news_rows = int(len(news_result))
                except Exception as e:
                    logger.warning(f"News refresh failed but pipeline will continue: {e}")
                    news_rows = 0

            features = self.build_features()
            feature_rows = int(len(features))

            ranking = self.build_ranking()
            ranking_rows = int(len(ranking))
            self.alert_dispatcher.top_ranking_changed(ranking)

            trading: dict[str, object] = {}
            if self.config.enable_paper_trading:
                logger.info("Continuous trading cycle using trader=%s", selected_trader_name())
                trading = self.pipeline.execute_trading_cycle(
                    ranking=ranking,
                    symbols=self.config.symbols,
                    interval=self.config.timeframe,
                )
                trades_executed = len(trading.get("trades", []))
                snapshot_saved = trading.get("snapshot") is not None
                for trade in trading.get("opened", []):
                    self.alert_dispatcher.trade_opened(trade)
                for trade in trading.get("closed", []):
                    self.alert_dispatcher.trade_closed(trade)
                snapshot = trading.get("snapshot")
                if isinstance(snapshot, dict) and trades_executed > 0:
                    self.alert_dispatcher.portfolio_snapshot(snapshot, label="Post-trade portfolio")

            cycle_result = ContinuousCycleResult(
                cycle_number=self._cycle_count,
                started_at=cycle_started_at,
                finished_at=utc_now(),
                symbols=self.config.symbols,
                timeframe=self.config.timeframe,
                market_rows=market_rows,
                feature_rows=feature_rows,
                ranking_rows=ranking_rows,
                trades_executed=trades_executed,
                news_rows=news_rows,
                snapshot_saved=snapshot_saved,
                success=True,
            )
            self._write_state(self._build_cycle_state("running", cycle_result))
            self.alert_dispatcher.pipeline_completed(
                {
                    "cycle_number": cycle_result.cycle_number,
                    "ranking_rows": cycle_result.ranking_rows,
                    "trades_executed": cycle_result.trades_executed,
                    "news_rows": cycle_result.news_rows,
                    "duration_seconds": cycle_result.duration_seconds,
                }
            )
            logger.info(
                "Continuous cycle #%s completed | market_rows=%s feature_rows=%s ranking_rows=%s trades=%s news_rows=%s",
                cycle_result.cycle_number,
                cycle_result.market_rows,
                cycle_result.feature_rows,
                cycle_result.ranking_rows,
                cycle_result.trades_executed,
                cycle_result.news_rows,
            )
            return cycle_result
        except Exception as exc:
            self._error_count += 1
            cycle_result = ContinuousCycleResult(
                cycle_number=self._cycle_count,
                started_at=cycle_started_at,
                finished_at=utc_now(),
                symbols=self.config.symbols,
                timeframe=self.config.timeframe,
                market_rows=market_rows,
                feature_rows=feature_rows,
                ranking_rows=ranking_rows,
                trades_executed=trades_executed,
                news_rows=news_rows,
                snapshot_saved=snapshot_saved,
                success=False,
                error_message=str(exc),
            )
            self._write_state(self._build_cycle_state("error", cycle_result))
            self.alert_dispatcher.critical_error(
                component="continuous_pipeline",
                error=str(exc),
                context={"cycle_number": self._cycle_count},
            )
            logger.exception("Continuous cycle #%s failed", self._cycle_count)
            return cycle_result

    def run(self, *, stop_event: threading.Event | None = None, max_cycles: int | None = None) -> list[ContinuousCycleResult]:
        """Run cycles until time limit, cycle limit or stop signal is reached."""
        stop_signal = stop_event or self._stop_event
        results: list[ContinuousCycleResult] = []
        started_at = utc_now()
        deadline = None if self.config.run_forever or self.config.duration_minutes is None else started_at + timedelta(minutes=self.config.duration_minutes)
        self._write_state({"status": "running", "started_at": started_at.isoformat(), "updated_at": self._now_iso()})

        while not stop_signal.is_set():
            cycle_started_monotonic = time.monotonic()
            results.append(self.run_cycle())

            if max_cycles is not None and len(results) >= max_cycles:
                break
            if deadline is not None and utc_now() >= deadline:
                break

            elapsed = time.monotonic() - cycle_started_monotonic
            sleep_seconds = max(0.0, self.config.cycle_interval_seconds - elapsed)
            if sleep_seconds > 0:
                time.sleep(sleep_seconds)

        self._write_state(
            {
                "status": "stopped",
                "stopped_at": self._now_iso(),
                "cycles_completed": self._cycle_count,
                "errors": self._error_count,
            }
        )
        return results

    def stop(self) -> None:
        """Signal the continuous loop to stop."""
        self._stop_event.set()
        self._write_state({"status": "stopping", "stopping_at": self._now_iso()})

    def get_state(self) -> dict[str, Any]:
        """Read the latest persisted continuous pipeline state."""
        if not self.state_path.exists():
            return {}
        return json.loads(self.state_path.read_text(encoding="utf-8"))

    def repository_path_for_scored_news(self) -> Path:
        """Return the canonical path for scored news used by ranking."""
        settings.scored_news_path.parent.mkdir(parents=True, exist_ok=True)
        return settings.scored_news_path

    def _should_refresh_news(self) -> bool:
        if not self.config.enable_news:
            return False
        if self._last_news_refresh_at is None:
            return True
        elapsed = safe_utc_diff(utc_now(), self._last_news_refresh_at).total_seconds()
        return elapsed >= self.config.news_refresh_interval_seconds

    def _validate_config(self) -> None:
        if self.config.cycle_interval_seconds <= 0:
            raise ValueError("cycle_interval_seconds must be greater than zero.")
        if self.config.news_refresh_interval_seconds <= 0:
            raise ValueError("news_refresh_interval_seconds must be greater than zero.")
        if self.config.candle_limit <= 0:
            raise ValueError("candle_limit must be greater than zero.")
        if not self.config.symbols:
            raise ValueError("At least one symbol is required.")
        if not self.config.timeframe.strip():
            raise ValueError("timeframe must not be empty.")

    def _build_cycle_state(self, status: str, cycle_result: ContinuousCycleResult) -> dict[str, Any]:
        latest_snapshot = self.repository.get_latest_snapshot()
        live_account = self.repository.get_live_account_view()
        account_snapshot = live_account.get("account_snapshot", {}) if isinstance(live_account, dict) else {}
        use_live_state = should_use_live_trader()
        return {
            "status": status,
            "updated_at": self._now_iso(),
            "cycle_number": cycle_result.cycle_number,
            "last_cycle_started_at": cycle_result.started_at.isoformat(),
            "last_cycle_finished_at": cycle_result.finished_at.isoformat(),
            "last_cycle_success": cycle_result.success,
            "last_cycle_error": cycle_result.error_message,
            "last_cycle_duration_seconds": cycle_result.duration_seconds,
            "last_ranking_at": self._last_ranking_at.isoformat() if self._last_ranking_at else None,
            "last_snapshot_at": self._last_snapshot_at.isoformat() if self._last_snapshot_at else None,
            "last_news_refresh_at": self._last_news_refresh_at.isoformat() if self._last_news_refresh_at else None,
            "cycles_completed": self._cycle_count,
            "errors": self._error_count,
            "open_positions": live_account.get("open_positions_count", 0) if use_live_state else len(latest_snapshot.get("positions_json", {})) if latest_snapshot else 0,
            "latest_equity": account_snapshot.get("total_balance") if use_live_state else latest_snapshot.get("equity") if latest_snapshot else None,
            "latest_cash": account_snapshot.get("free_balance") if use_live_state else latest_snapshot.get("cash") if latest_snapshot else None,
        }

    def _write_state(self, payload: dict[str, Any]) -> None:
        state = self.get_state()
        state.update(payload)
        self.state_path.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")

    @staticmethod
    def _now_iso() -> str:
        return utc_now().isoformat()
