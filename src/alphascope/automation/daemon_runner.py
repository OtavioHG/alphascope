"""Daemon-style orchestrator for continuous AlphaScope runtime."""

from __future__ import annotations

import json
import os
import signal
import threading
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from alphascope.alerts import AlertDispatcher
from alphascope.automation.continuous_pipeline import ContinuousPipeline, ContinuousPipelineConfig
from alphascope.automation.heartbeat import HeartbeatConfig, HeartbeatService
from alphascope.automation.scheduler import AutomationScheduler
from alphascope.config.settings import settings
from alphascope.core.logger import get_logger

logger = get_logger(__name__)


@dataclass(slots=True)
class DaemonRunnerConfig:
    """Runtime configuration for the AlphaScope daemon runner."""

    symbols: list[str]
    timeframe: str
    candle_limit: int
    cycle_interval_seconds: int = settings.cycle_interval_seconds
    news_refresh_interval_seconds: int = settings.news_refresh_interval_seconds
    heartbeat_interval_seconds: int = settings.heartbeat_interval_seconds
    enable_scheduler: bool = settings.enable_scheduler
    enable_continuous_pipeline: bool = settings.enable_continuous_pipeline
    register_scheduler_jobs: bool = True
    pid_file: Path = settings.daemon_pid_file
    status_file: Path = settings.daemon_status_file
    heartbeat_file: Path = settings.heartbeat_file
    max_consecutive_errors: int = settings.max_consecutive_errors
    retry_backoff_seconds: int = settings.retry_backoff_seconds
    enable_news: bool = True
    enable_market_refresh: bool = True
    enable_paper_trading: bool = True


class DaemonRunner:
    """Manage a local long-running AlphaScope process with graceful shutdown."""

    def __init__(
        self,
        config: DaemonRunnerConfig,
        *,
        scheduler: AutomationScheduler | None = None,
        continuous_pipeline: ContinuousPipeline | None = None,
        heartbeat_service: HeartbeatService | None = None,
        alert_dispatcher: AlertDispatcher | None = None,
    ) -> None:
        self.config = config
        self.config.pid_file.parent.mkdir(parents=True, exist_ok=True)
        self.config.status_file.parent.mkdir(parents=True, exist_ok=True)
        self.config.heartbeat_file.parent.mkdir(parents=True, exist_ok=True)
        self._stop_event = threading.Event()
        self._consecutive_errors = 0
        self._started_at: datetime | None = None
        self._cycle_count = 0
        self._previous_signal_handlers: dict[int, Any] = {}
        self.alert_dispatcher = alert_dispatcher or AlertDispatcher()

        pipeline_config = ContinuousPipelineConfig(
            cycle_interval_seconds=config.cycle_interval_seconds,
            news_refresh_interval_seconds=config.news_refresh_interval_seconds,
            symbols=config.symbols,
            timeframe=config.timeframe,
            candle_limit=config.candle_limit,
            enable_news=config.enable_news,
            enable_market_refresh=config.enable_market_refresh,
            enable_paper_trading=config.enable_paper_trading,
            run_forever=True,
        )
        self.continuous_pipeline = continuous_pipeline or ContinuousPipeline(
            pipeline_config,
            state_path=self.config.status_file.parent / "continuous_pipeline_status.json",
        )
        self.scheduler = scheduler or AutomationScheduler(
            state_path=self.config.status_file.parent / "scheduler_status.json",
        )
        if config.enable_scheduler and config.register_scheduler_jobs and hasattr(self.scheduler, "register_pipeline_jobs"):
            self.scheduler.register_pipeline_jobs(
                self.continuous_pipeline,
                market_interval_seconds=config.cycle_interval_seconds,
                news_interval_seconds=config.news_refresh_interval_seconds,
                feature_interval_seconds=config.cycle_interval_seconds,
                ranking_interval_seconds=config.cycle_interval_seconds,
                paper_trading_interval_seconds=config.cycle_interval_seconds,
                max_retries=1,
                retry_backoff_seconds=config.retry_backoff_seconds,
            )

        self.heartbeat_service = heartbeat_service or HeartbeatService(
            HeartbeatConfig(
                interval_seconds=config.heartbeat_interval_seconds,
                heartbeat_file=config.heartbeat_file,
            ),
            payload_provider=self._heartbeat_payload,
        )

    def start(self, *, max_cycles: int | None = None, run_duration_seconds: int | None = None) -> dict[str, Any]:
        """Start the daemon loop and keep it alive until stopped."""
        self._validate_startup()
        self._started_at = datetime.now(UTC)
        self._write_pid_file()
        self._write_status("starting")
        self._install_signal_handlers()
        self.heartbeat_service.start()
        logger.info("AlphaScope daemon started with pid=%s", os.getpid())

        started_monotonic = time.monotonic()
        pending_error: Exception | None = None
        try:
            self._write_status("running")
            while not self._stop_event.is_set():
                if run_duration_seconds is not None and (time.monotonic() - started_monotonic) >= run_duration_seconds:
                    break
                if self.config.enable_scheduler:
                    self.scheduler.run_pending()
                if self.config.enable_continuous_pipeline:
                    result = self.continuous_pipeline.run_cycle()
                    self._cycle_count += 1
                    if result.success:
                        self._consecutive_errors = 0
                    else:
                        self._consecutive_errors += 1
                        if self._consecutive_errors >= self.config.max_consecutive_errors:
                            raise RuntimeError(
                                f"Daemon stopped after {self._consecutive_errors} consecutive cycle errors."
                            )
                if max_cycles is not None and self._cycle_count >= max_cycles:
                    break
                time.sleep(max(1, self.config.cycle_interval_seconds))
        except KeyboardInterrupt:
            logger.info("Daemon interrupted by user")
            self._write_status("interrupted", last_error="KeyboardInterrupt")
        except Exception as exc:
            logger.exception("Daemon runner failed")
            self._write_status("error", last_error=str(exc))
            self.alert_dispatcher.critical_error(component="daemon_runner", error=str(exc))
            pending_error = exc
        finally:
            final_status = self.stop()
            self._restore_signal_handlers()
        if pending_error is not None:
            raise pending_error
        return final_status

    def stop(self) -> dict[str, Any]:
        """Gracefully stop daemon services and persist final status."""
        self._stop_event.set()
        self.scheduler.stop()
        self.continuous_pipeline.stop()
        self.heartbeat_service.stop()
        final_status = self._write_status("stopped")
        if self.config.pid_file.exists():
            self.config.pid_file.unlink()
        self.alert_dispatcher.daemon_stopped(final_status)
        logger.info("AlphaScope daemon stopped")
        return final_status

    def request_stop(self) -> None:
        """Request daemon shutdown from external callers."""
        self._stop_event.set()
        self._write_status("stop_requested")

    def status(self) -> dict[str, Any]:
        """Return the latest persisted daemon status."""
        if not self.config.status_file.exists():
            return {
                "status": "not_running",
                "pid": None,
                "scheduler": self.scheduler.get_state(),
                "continuous_pipeline": self.continuous_pipeline.get_state(),
                "heartbeat": self._read_heartbeat(),
            }
        payload = json.loads(self.config.status_file.read_text(encoding="utf-8"))
        payload["scheduler"] = self.scheduler.get_state()
        payload["continuous_pipeline"] = self.continuous_pipeline.get_state()
        payload["heartbeat"] = self._read_heartbeat()
        return payload

    def _validate_startup(self) -> None:
        if self.config.pid_file.exists():
            raise RuntimeError(f"Daemon pid file already exists: {self.config.pid_file}")
        if not self.config.symbols:
            raise ValueError("Daemon runner requires at least one symbol.")
        if self.config.cycle_interval_seconds <= 0:
            raise ValueError("cycle_interval_seconds must be greater than zero.")
        if not self.config.enable_scheduler and not self.config.enable_continuous_pipeline:
            raise ValueError("Daemon runner requires at least one active service: scheduler or continuous pipeline.")

    def _write_pid_file(self) -> None:
        self.config.pid_file.write_text(str(os.getpid()), encoding="utf-8")

    def _write_status(self, status: str, *, last_error: str | None = None) -> dict[str, Any]:
        payload = {
            "status": status,
            "pid": os.getpid(),
            "started_at": self._started_at.isoformat() if self._started_at else None,
            "updated_at": datetime.now(UTC).isoformat(),
            "cycle_count": self._cycle_count,
            "consecutive_errors": self._consecutive_errors,
            "symbols": self.config.symbols,
            "timeframe": self.config.timeframe,
            "candle_limit": self.config.candle_limit,
            "scheduler_enabled": self.config.enable_scheduler,
            "continuous_pipeline_enabled": self.config.enable_continuous_pipeline,
            "last_error": last_error,
        }
        self.config.status_file.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return payload

    def _read_heartbeat(self) -> dict[str, Any]:
        if not self.config.heartbeat_file.exists():
            return {}
        return json.loads(self.config.heartbeat_file.read_text(encoding="utf-8"))

    def _heartbeat_payload(self) -> dict[str, Any]:
        return {
            "daemon_status": "running" if not self._stop_event.is_set() else "stopping",
            "cycle_count": self._cycle_count,
            "consecutive_errors": self._consecutive_errors,
        }

    def _install_signal_handlers(self) -> None:
        if threading.current_thread() is not threading.main_thread():
            return

        def _handle_signal(signum: int, _frame: Any) -> None:
            logger.info("Daemon received signal %s", signum)
            self.request_stop()

        for signum in (signal.SIGINT, signal.SIGTERM):
            try:
                self._previous_signal_handlers[signum] = signal.getsignal(signum)
                signal.signal(signum, _handle_signal)
            except (ValueError, OSError):
                continue

    def _restore_signal_handlers(self) -> None:
        if threading.current_thread() is not threading.main_thread():
            return
        for signum, handler in self._previous_signal_handlers.items():
            try:
                signal.signal(signum, handler)
            except (ValueError, OSError):
                continue
        self._previous_signal_handlers.clear()
