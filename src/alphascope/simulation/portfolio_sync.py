"""Load and persist simulated portfolio state using the main storage repository."""

from __future__ import annotations

from dataclasses import asdict

from alphascope.execution.portfolio import Portfolio, Position
from alphascope.storage.repositories import StorageRepository
from alphascope.utils.time import utc_now


class PortfolioSync:
    """Synchronize simulation portfolio state with persistent storage."""

    def __init__(self, repository: StorageRepository | None = None) -> None:
        self.repository = repository or StorageRepository()

    def load(self, *, initial_cash: float) -> Portfolio:
        """Restore the latest portfolio snapshot from storage."""
        snapshot = self.repository.get_latest_snapshot()
        if snapshot is None:
            return Portfolio(cash=initial_cash)

        positions = {
            symbol: Position(**position_data)
            for symbol, position_data in dict(snapshot.get("positions_json", {})).items()
        }
        return Portfolio(
            cash=float(snapshot.get("cash", initial_cash)),
            realized_pnl=float(snapshot.get("realized_pnl", 0.0)),
            positions=positions,
        )

    def save(
        self,
        *,
        portfolio: Portfolio,
        trades: list[dict[str, object]],
        persist_trades: bool = True,
    ) -> dict[str, object]:
        """Persist trades and portfolio snapshot using the standard storage format."""
        snapshot = {
            "timestamp": utc_now(),
            "cash": portfolio.cash,
            "equity": portfolio.equity(),
            "realized_pnl": portfolio.realized_pnl,
            "unrealized_pnl": portfolio.unrealized_pnl(),
            "positions_json": {
                symbol: asdict(position)
                for symbol, position in portfolio.positions.items()
            },
        }
        if persist_trades and trades:
            self.repository.save_trades(trades)
        self.repository.save_snapshot(snapshot)
        return snapshot
