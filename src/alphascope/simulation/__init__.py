"""Live-simulated trading primitives for AlphaScope."""

from alphascope.simulation.event_loop import EventLoop, EventLoopConfig
from alphascope.simulation.execution_simulator import ExecutionSimulator, SimulationExecutionResult
from alphascope.simulation.live_simulator import LiveSimulationConfig, LiveSimulationCycleResult, LiveSimulator
from alphascope.simulation.portfolio_sync import PortfolioSync
from alphascope.simulation.signal_dispatcher import Signal, SignalDispatcher

__all__ = [
    "EventLoop",
    "EventLoopConfig",
    "ExecutionSimulator",
    "LiveSimulationConfig",
    "LiveSimulationCycleResult",
    "LiveSimulator",
    "PortfolioSync",
    "Signal",
    "SignalDispatcher",
    "SimulationExecutionResult",
]
