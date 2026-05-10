"""Central aggregation layer for external crypto data sources."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from alphascope.config.settings import settings
from alphascope.core.logger import get_logger
from alphascope.external_data.binance_source import BinanceMarketSource
from alphascope.external_data.coinmarketcap_source import CoinMarketCapMarketSource
from alphascope.external_data.coingecko_source import CoinGeckoMarketSource

logger = get_logger(__name__)


class MarketDataAggregator:
    """Aggregate normalized market data from multiple external sources."""

    def __init__(self) -> None:
        self.sources = self._build_sources()
        self.data_dir = settings.market_universe_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def fetch_market_universe(
        self,
        *,
        primary_source: str | None = None,
        fallback_sources: list[str] | None = None,
        limit: int = 250,
        persist: bool = True,
    ) -> pd.DataFrame:
        source_order = self._resolve_source_order(primary_source, fallback_sources)
        raw_frames = self.fetch_source_snapshots(source_order=source_order, limit=limit, persist=persist)
        if not raw_frames:
            raise RuntimeError("No external data source returned market data.")
        consolidated = self._consolidate(raw_frames, primary_source=source_order[0])
        if persist:
            self._save_frame(consolidated, self.data_dir / "market_universe_latest.csv")
        return consolidated

    def fetch_source_snapshots(
        self,
        *,
        source_order: list[str] | None = None,
        limit: int = 250,
        persist: bool = False,
    ) -> dict[str, pd.DataFrame]:
        order = source_order or self._resolve_source_order(None, None)
        snapshots: dict[str, pd.DataFrame] = {}
        for source_name in order:
            source = self.sources.get(source_name)
            if source is None:
                continue
            try:
                frame = source.fetch_market_snapshot(limit=limit)
                if frame.empty:
                    logger.warning("Source %s returned an empty snapshot.", source_name)
                    continue
                snapshots[source_name] = frame
                if persist:
                    self._save_frame(frame, self.data_dir / f"{source_name}_snapshot_latest.csv")
            except Exception as exc:
                logger.warning("External source %s failed: %s", source_name, exc)
        if persist and snapshots:
            combined = pd.concat(snapshots.values(), ignore_index=True)
            self._save_frame(combined, self.data_dir / "market_universe_sources_latest.csv")
        return snapshots

    def compare_sources(self, symbol: str | None = None, limit: int = 50) -> pd.DataFrame:
        snapshots = self.fetch_source_snapshots(limit=limit, persist=False)
        if not snapshots:
            return pd.DataFrame()
        combined = pd.concat(snapshots.values(), ignore_index=True)
        if symbol:
            combined = combined.loc[combined["canonical_symbol"] == symbol.upper()].reset_index(drop=True)
        comparison_columns = [
            "source",
            "canonical_symbol",
            "price",
            "volume_24h",
            "market_cap",
            "rank",
            "timestamp",
        ]
        return combined.loc[:, comparison_columns].sort_values(["canonical_symbol", "source"]).reset_index(drop=True)

    def load_saved_universe(self) -> pd.DataFrame:
        path = self.data_dir / "market_universe_latest.csv"
        if not path.exists():
            return pd.DataFrame()
        return pd.read_csv(path)

    def load_saved_snapshot(self, source_name: str) -> pd.DataFrame:
        path = self.data_dir / f"{source_name}_snapshot_latest.csv"
        if not path.exists():
            return pd.DataFrame()
        return pd.read_csv(path)

    def _build_sources(self) -> dict[str, object]:
        sources: dict[str, object] = {}
        if settings.binance_api_enabled:
            sources["binance"] = BinanceMarketSource()
        if settings.coingecko_api_enabled:
            sources["coingecko"] = CoinGeckoMarketSource()
        if settings.coinmarketcap_api_enabled:
            sources["coinmarketcap"] = CoinMarketCapMarketSource()
        return sources

    def _resolve_source_order(self, primary_source: str | None, fallback_sources: list[str] | None) -> list[str]:
        primary = (primary_source or settings.primary_market_source).strip().lower()
        fallbacks = fallback_sources or settings.fallback_sources_list
        order = [primary] + [item.strip().lower() for item in fallbacks if item.strip()]
        resolved = []
        for item in order:
            if item in self.sources and item not in resolved:
                resolved.append(item)
        if not resolved:
            resolved = list(self.sources.keys())
        return resolved

    def _consolidate(self, snapshots: dict[str, pd.DataFrame], primary_source: str) -> pd.DataFrame:
        combined = pd.concat(snapshots.values(), ignore_index=True)
        if combined.empty:
            return combined

        source_priority = {primary_source: 0}
        for index, source_name in enumerate(snapshots.keys(), start=1):
            source_priority.setdefault(source_name, index)

        combined["source_priority"] = combined["source"].map(lambda value: source_priority.get(value, 999))
        combined["completeness_score"] = combined[["price", "volume_24h", "market_cap", "rank"]].notna().sum(axis=1)
        combined = combined.sort_values(
            ["canonical_symbol", "source_priority", "completeness_score", "market_cap", "volume_24h"],
            ascending=[True, True, False, False, False],
        )
        consolidated = combined.drop_duplicates(subset=["canonical_symbol"], keep="first").reset_index(drop=True)
        consolidated = consolidated.drop(columns=["source_priority", "completeness_score"])
        return consolidated.sort_values(["rank", "market_cap", "volume_24h"], ascending=[True, False, False], na_position="last").reset_index(drop=True)

    @staticmethod
    def _save_frame(frame: pd.DataFrame, path: Path) -> None:
        serializable = frame.copy()
        if "extra_metadata" in serializable.columns:
            serializable["extra_metadata"] = serializable["extra_metadata"].map(
                lambda value: json.dumps(value, ensure_ascii=False) if isinstance(value, dict) else value
            )
        serializable.to_csv(path, index=False)
