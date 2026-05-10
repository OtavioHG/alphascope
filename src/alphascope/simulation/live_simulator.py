"""Live-style simulated trading loop built on AlphaScope ranking outputs."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from alphascope.alerts import AlertDispatcher
from alphascope.config.settings import settings
from alphascope.core.logger import get_logger
from alphascope.core.pipeline import AlphaScopePipeline
from alphascope.simulation.event_loop import EventLoop, EventLoopConfig
from alphascope.simulation.execution_simulator import ExecutionSimulator
from alphascope.simulation.portfolio_sync import PortfolioSync
from alphascope.simulation.signal_dispatcher import SignalDispatcher

logger = get_logger(__name__)


@dataclass(slots=True)
class LiveSimulationConfig:
    """Configuration for live-simulated continuous trading."""

    symbols: list[str]
    timeframe: str
    candle_limit: int
    cycle_interval_seconds: int = settings.cycle_interval_seconds
    mode: str = "live_simulated"
    run_forever: bool = True
    duration_minutes: int | None = None
    state_path: Path = settings.runtime_dir / "live_simulated_status.json"
    initial_cash: float = settings.paper_initial_cash


@dataclass(slots=True)
class LiveSimulationCycleResult:
    """Summary for a live-simulated cycle."""

    cycle_number: int
    started_at: datetime
    finished_at: datetime
    mode: str
    signals: int
    trades: int
    open_positions: int
    equity: float
    cash: float
    success: bool
    error_message: str | None = None


class LiveSimulator:
    """Run live-style simulated execution from current market rankings."""

    def __init__(
        self,
        config: LiveSimulationConfig,
        *,
        pipeline: AlphaScopePipeline | None = None,
        dispatcher: SignalDispatcher | None = None,
        execution_simulator: ExecutionSimulator | None = None,
        portfolio_sync: PortfolioSync | None = None,
        event_loop: EventLoop | None = None,
        alert_dispatcher: AlertDispatcher | None = None,
    ) -> None:
        self.config = config
        self.config.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.pipeline = pipeline or AlphaScopePipeline()
        self.dispatcher = dispatcher or SignalDispatcher()
        self.execution_simulator = execution_simulator or ExecutionSimulator()
        self.portfolio_sync = portfolio_sync or PortfolioSync(repository=self.pipeline.repository)
        self.event_loop = event_loop or EventLoop(
            EventLoopConfig(
                cycle_interval_seconds=config.cycle_interval_seconds,
                run_forever=config.run_forever,
                duration_minutes=config.duration_minutes,
            )
        )
        self.portfolio = self.portfolio_sync.load(initial_cash=config.initial_cash)
        self.alert_dispatcher = alert_dispatcher or AlertDispatcher()
        self._cycle_count = 0
        self._write_state({"status": "initialized", "updated_at": self._now_iso()})

    def run_cycle(self) -> LiveSimulationCycleResult:
        """Execute one live-simulated trading cycle."""
        self._cycle_count += 1
        started_at = datetime.now(UTC)
        try:
            ranking = self.pipeline.rank_assets(self.config.symbols, self.config.timeframe)
            self.alert_dispatcher.top_ranking_changed(ranking)
            latest_prices = self._latest_prices()
            self.execution_simulator.mark_to_market(self.portfolio, latest_prices)
            signals = self.dispatcher.dispatch(ranking, latest_prices, set(self.portfolio.positions.keys()))
            execution = self.execution_simulator.execute(signals, self.portfolio)

            if self.config.mode == "live_simulated":
                snapshot = self.portfolio_sync.save(
                    portfolio=self.portfolio,
                    trades=execution.trades,
                    persist_trades=True,
                )
            else:
                snapshot = {
                    "timestamp": datetime.now(UTC),
                    "cash": self.portfolio.cash,
                    "equity": self.portfolio.equity(),
                    "realized_pnl": self.portfolio.realized_pnl,
                    "unrealized_pnl": self.portfolio.unrealized_pnl(),
                    "positions_json": {symbol: vars(position) for symbol, position in self.portfolio.positions.items()},
                }
            for trade in execution.trades:
                side = str(trade.get("side", "")).upper()
                if side == "SELL":
                    self.alert_dispatcher.trade_closed(trade)
                else:
                    self.alert_dispatcher.trade_opened(trade)
            if execution.trades:
                self.alert_dispatcher.portfolio_snapshot(snapshot, label="Live simulated portfolio")

            result = LiveSimulationCycleResult(
                cycle_number=self._cycle_count,
                started_at=started_at,
                finished_at=datetime.now(UTC),
                mode=self.config.mode,
                signals=len(signals),
                trades=len(execution.trades),
                open_positions=len(self.portfolio.positions),
                equity=float(snapshot["equity"]),
                cash=float(snapshot["cash"]),
                success=True,
            )
            self._write_state(self._build_state(result))
            logger.info(
                "Live simulator cycle #%s completed | mode=%s signals=%s trades=%s open_positions=%s",
                result.cycle_number,
                result.mode,
                result.signals,
                result.trades,
                result.open_positions,
            )
            return result
        except Exception as exc:
            self.alert_dispatcher.critical_error(component="live_simulator", error=str(exc))
            result = LiveSimulationCycleResult(
                cycle_number=self._cycle_count,
                started_at=started_at,
                finished_at=datetime.now(UTC),
                mode=self.config.mode,
                signals=0,
                trades=0,
                open_positions=len(self.portfolio.positions),
                equity=self.portfolio.equity(),
                cash=self.portfolio.cash,
                success=False,
                error_message=str(exc),
            )
            self._write_state(self._build_state(result))
            logger.exception("Live simulator cycle #%s failed", self._cycle_count)
            return result

    def run(self, *, max_cycles: int | None = None) -> list[LiveSimulationCycleResult]:
        """Run the live simulator event loop."""
        self._write_state({"status": "running", "updated_at": self._now_iso()})
        return self.event_loop.run(self.run_cycle, max_cycles=max_cycles)

    def stop(self) -> None:
        """Stop the live simulator loop."""
        self.event_loop.stop()
        self._write_state({"status": "stopped", "updated_at": self._now_iso()})

    def get_state(self) -> dict[str, Any]:
        """Read the latest simulator state."""
        if not self.config.state_path.exists():
            return {}
        return json.loads(self.config.state_path.read_text(encoding="utf-8"))

    def _latest_prices(self) -> dict[str, float]:
        prices: dict[str, float] = {}
        for symbol in self.config.symbols:
            candles = self.pipeline.repository.get_candles(symbol=symbol, interval=self.config.timeframe, limit=1)
            if not candles.empty:
                prices[symbol] = float(candles.iloc[-1]["close"])
        return prices

    def _build_state(self, result: LiveSimulationCycleResult) -> dict[str, Any]:
        return {
            "status": "running" if result.success else "error",
            "updated_at": self._now_iso(),
            "cycle_number": result.cycle_number,
            "mode": result.mode,
            "signals": result.signals,
            "trades": result.trades,
            "open_positions": result.open_positions,
            "equity": result.equity,
            "cash": result.cash,
            "last_cycle_started_at": result.started_at.isoformat(),
            "last_cycle_finished_at": result.finished_at.isoformat(),
            "last_cycle_success": result.success,
            "last_cycle_error": result.error_message,
        }

    def _write_state(self, payload: dict[str, Any]) -> None:
        state = self.get_state()
        state.update(payload)
        self.config.state_path.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(UTC).isoformat()
