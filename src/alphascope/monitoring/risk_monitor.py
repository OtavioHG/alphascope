from __future__ import annotations

import pandas as pd


class RiskMonitor:
    def evaluate(
        self,
        portfolio_snapshot: dict[str, float],
        positions: pd.DataFrame | None = None,
    ) -> dict[str, object]:
        total_equity = float(portfolio_snapshot.get("total_equity", portfolio_snapshot.get("equity", 0.0)))
        available_capital = float(portfolio_snapshot.get("available_capital", portfolio_snapshot.get("cash_balance", 0.0)))
        exposure = 0.0 if total_equity == 0 else max(0.0, 1.0 - (available_capital / total_equity))
        concentration = 0.0
        volatility_proxy = 0.0
        if positions is not None and not positions.empty:
            values = positions.get("allocation_amount", positions.get("quantity", pd.Series(dtype=float))).astype(float)
            total = float(values.sum()) if len(values) else 0.0
            concentration = float(values.max() / total) if total > 0 else 0.0
            volatility_proxy = float(positions.get("unrealized_pnl", pd.Series(dtype=float)).astype(float).std(ddof=0) or 0.0)
        alerts = []
        if exposure > 0.75:
            alerts.append("high_exposure")
        if concentration > 0.4:
            alerts.append("high_concentration")
        return {
            "drawdown": float(portfolio_snapshot.get("portfolio_return", 0.0) * -1 if portfolio_snapshot.get("portfolio_return", 0.0) < 0 else 0.0),
            "exposure": exposure,
            "volatility_proxy": volatility_proxy,
            "concentration": concentration,
            "alerts": alerts,
        }
