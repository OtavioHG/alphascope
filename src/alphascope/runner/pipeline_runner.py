"""Utilities to execute the AlphaScope pipeline in a timed loop."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from alphascope.core.pipeline import AlphaScopePipeline

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class PipelineRunLoopConfig:
    """Configuration for repeated pipeline execution."""

    duration_minutes: int
    interval_seconds: int
    symbols: list[str]
    timeframe: str
    limit: int


@dataclass(slots=True)
class PipelineRunLoopResult:
    """Summary produced after the loop finishes."""

    started_at: datetime
    finished_at: datetime
    duration_minutes: int
    interval_seconds: int
    total_runs: int
    successful_runs: int
    failed_runs: int
    symbols: list[str]
    timeframe: str
    limit: int

    @property
    def elapsed_seconds(self) -> float:
        """Return total execution time in seconds."""
        return (self.finished_at - self.started_at).total_seconds()


class PipelineRunner:
    """Run the AlphaScope pipeline repeatedly until a time limit is reached."""

    def __init__(self, pipeline: AlphaScopePipeline | None = None) -> None:
        self.pipeline = pipeline or AlphaScopePipeline()

    def run_loop(self, config: PipelineRunLoopConfig) -> PipelineRunLoopResult:
        """Execute the pipeline until the configured duration expires."""
        self._validate_config(config)

        started_at = datetime.now(UTC)
        deadline = started_at + timedelta(minutes=config.duration_minutes)
        total_runs = 0
        successful_runs = 0
        failed_runs = 0

        logger.info("AlphaScope Pipeline Runner")
        logger.info("Duration: %s minutes", config.duration_minutes)
        logger.info("Interval: %s seconds", config.interval_seconds)
        logger.info("Symbols: %s", ", ".join(config.symbols))
        logger.info("Timeframe: %s", config.timeframe)
        logger.info("Limit: %s", config.limit)

        while datetime.now(UTC) < deadline:
            total_runs += 1
            logger.info("Run #%s started", total_runs)

            try:
                result = self.pipeline.run_pipeline(
                    symbols=config.symbols,
                    interval=config.timeframe,
                    limit=config.limit,
                )
            except Exception:
                failed_runs += 1
                logger.exception("Run #%s failed", total_runs)
                logger.warning("run_loop continuing after error | run=%s", total_runs)
            else:
                successful_runs += 1
                logger.info(
                    "Run #%s completed | symbols=%s feature_rows=%s ranking_rows=%s paper_trades=%s",
                    total_runs,
                    len(result.get("symbols", [])),
                    result.get("feature_rows", 0),
                    result.get("ranking_rows", 0),
                    result.get("paper_trades", 0),
                )

            now = datetime.now(UTC)
            if now >= deadline:
                break

            remaining_seconds = (deadline - now).total_seconds()
            sleep_seconds = min(config.interval_seconds, max(0.0, remaining_seconds))
            if sleep_seconds <= 0:
                break
            logger.info("Waiting %.0f seconds before next run", sleep_seconds)
            time.sleep(sleep_seconds)

        finished_at = datetime.now(UTC)
        summary = PipelineRunLoopResult(
            started_at=started_at,
            finished_at=finished_at,
            duration_minutes=config.duration_minutes,
            interval_seconds=config.interval_seconds,
            total_runs=total_runs,
            successful_runs=successful_runs,
            failed_runs=failed_runs,
            symbols=config.symbols,
            timeframe=config.timeframe,
            limit=config.limit,
        )
        self._log_summary(summary)
        return summary

    @staticmethod
    def _validate_config(config: PipelineRunLoopConfig) -> None:
        """Validate loop configuration before execution."""
        if config.duration_minutes <= 0:
            raise ValueError("duration_minutes must be greater than zero.")
        if config.interval_seconds < 0:
            raise ValueError("interval_seconds must be zero or greater.")
        if config.limit <= 0:
            raise ValueError("limit must be greater than zero.")
        if not config.timeframe.strip():
            raise ValueError("timeframe must not be empty.")
        if not config.symbols:
            raise ValueError("At least one symbol is required.")

    @staticmethod
    def _log_summary(summary: PipelineRunLoopResult) -> None:
        """Emit a final execution summary to the terminal logs."""
        logger.info("Pipeline loop finished")
        logger.info("Total runs executed: %s", summary.total_runs)
        logger.info("Successful runs: %s", summary.successful_runs)
        logger.info("Failed runs: %s", summary.failed_runs)
        logger.info("Elapsed seconds: %.2f", summary.elapsed_seconds)

    @staticmethod
    def result_to_dict(summary: PipelineRunLoopResult) -> dict[str, Any]:
        """Convert the loop result to a CLI-friendly dictionary."""
        return {
            "started_at": summary.started_at,
            "finished_at": summary.finished_at,
            "duration_minutes": summary.duration_minutes,
            "interval_seconds": summary.interval_seconds,
            "total_runs": summary.total_runs,
            "successful_runs": summary.successful_runs,
            "failed_runs": summary.failed_runs,
            "symbols": summary.symbols,
            "timeframe": summary.timeframe,
            "limit": summary.limit,
            "elapsed_seconds": summary.elapsed_seconds,
        }
