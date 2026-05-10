from __future__ import annotations

from pathlib import Path

import pandas as pd


class StrategyMarketplace:
    def __init__(self, output_dir: str = "data/processed/marketplace"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def build_listing(self, registry: pd.DataFrame, health: pd.DataFrame | None = None) -> pd.DataFrame:
        if registry.empty:
            return pd.DataFrame()
        listing = registry.copy()
        if health is not None and not health.empty:
            keep = [column for column in ["strategy_id", "robustness_score", "rolling_sharpe", "degradation_level"] if column in health.columns]
            if keep:
                listing = listing.merge(health[keep], on="strategy_id", how="left")
        listing["marketplace_score"] = (
            listing.get("robustness_score", pd.Series(0.0, index=listing.index)).fillna(0.0) * 0.6
            + listing.get("rolling_sharpe", pd.Series(0.0, index=listing.index)).fillna(0.0) * 0.4
        )
        listing = listing.sort_values("marketplace_score", ascending=False).reset_index(drop=True)
        listing.to_csv(self.output_dir / "strategy_marketplace.csv", index=False)
        return listing
