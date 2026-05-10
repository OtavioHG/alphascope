"""Automatic Binance market universe builder."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from time import sleep
from typing import Any

import pandas as pd
import requests

from alphascope.config.settings import settings
from alphascope.core.logger import get_logger
from alphascope.universe.filters import is_desired_spot_symbol, is_quote_asset_allowed, is_trading_symbol
from alphascope.utils.io import ensure_directory

logger = get_logger(__name__)


@dataclass(frozen=True)
class UniverseBuildResult:
    """Structured response for an automatic universe build."""

    all_assets: pd.DataFrame
    selected_assets: pd.DataFrame
    output_path: Path


class BinanceUniverseBuilder:
    """Build a ranked liquid spot universe from Binance public endpoints."""

    def __init__(
        self,
        *,
        base_url: str | None = None,
        timeout: int | None = None,
        max_retries: int | None = None,
        session: requests.Session | None = None,
    ) -> None:
        self.base_url = (base_url or settings.binance_base_url).rstrip("/")
        self.timeout = timeout or settings.request_timeout
        self.max_retries = max_retries or settings.request_retries
        self.session = session or requests.Session()

    def build(
        self,
        *,
        top: int = 200,
        quote_asset: str = "USDT",
        min_volume: float = 10_000_000.0,
        persist: bool = True,
        output_path: Path | None = None,
    ) -> UniverseBuildResult:
        """Fetch, filter, rank and optionally persist the automatic universe."""
        normalized_quote = quote_asset.upper()
        exchange_frame = self._fetch_exchange_info()
        ticker_frame = self._fetch_ticker_24h()

        eligible = exchange_frame.loc[
            exchange_frame["quote_asset"].map(lambda value: is_quote_asset_allowed(value, normalized_quote))
            & exchange_frame["status"].map(is_trading_symbol)
            & exchange_frame.apply(
                lambda row: is_desired_spot_symbol(row.get("base_asset"), row.get("quote_asset")),
                axis=1,
            )
        ].copy()

        merged = eligible.merge(
            ticker_frame.loc[:, ["symbol", "volume_24h", "last_price"]],
            on="symbol",
            how="left",
        )
        merged["volume_24h"] = pd.to_numeric(merged["volume_24h"], errors="coerce")
        merged["last_price"] = pd.to_numeric(merged["last_price"], errors="coerce")
        merged = merged.dropna(subset=["volume_24h", "last_price"]).reset_index(drop=True)
        merged = merged.loc[merged["volume_24h"] >= float(min_volume)].copy()
        merged = merged.sort_values(["volume_24h", "symbol"], ascending=[False, True]).reset_index(drop=True)
        merged["rank_volume"] = range(1, len(merged) + 1)
        merged["selected"] = merged["rank_volume"] <= int(top)

        ranked_columns = ["symbol", "quote_asset", "volume_24h", "last_price", "rank_volume", "selected"]
        ranked = merged.loc[:, ranked_columns].copy()
        selected = ranked.loc[ranked["selected"]].reset_index(drop=True)
        destination = output_path or self._default_output_path(top=top)

        if persist:
            self.save(selected, output_path=destination)
            latest_path = settings.processed_data_dir / "market_universe_latest.csv"
            self.save(selected, output_path=latest_path)

        logger.info(
            "Automatic universe built with %s selected assets from %s eligible Binance pairs",
            len(selected),
            len(ranked),
        )
        return UniverseBuildResult(all_assets=ranked, selected_assets=selected, output_path=destination)

    def load(self, path: Path | None = None) -> pd.DataFrame:
        """Load a previously persisted automatic universe."""
        target_path = path or settings.auto_universe_path
        if not target_path.exists():
            return pd.DataFrame(columns=["symbol", "quote_asset", "volume_24h", "last_price", "rank_volume", "selected"])
        frame = pd.read_csv(target_path)
        if "selected" in frame.columns:
            frame["selected"] = frame["selected"].map(
                lambda value: str(value).strip().lower() in {"1", "true", "yes", "y"}
            )
        return frame

    def save(self, frame: pd.DataFrame, *, output_path: Path) -> Path:
        """Persist the universe to CSV."""
        ensure_directory(output_path.parent)
        frame.to_csv(output_path, index=False)
        return output_path

    def _fetch_exchange_info(self) -> pd.DataFrame:
        payload = self._request_json("/api/v3/exchangeInfo")
        rows: list[dict[str, object]] = []
        for item in payload.get("symbols", []):
            rows.append(
                {
                    "symbol": str(item.get("symbol", "")).upper(),
                    "base_asset": str(item.get("baseAsset", "")).upper(),
                    "quote_asset": str(item.get("quoteAsset", "")).upper(),
                    "status": str(item.get("status", "")).upper(),
                }
            )
        return pd.DataFrame(rows)

    def _fetch_ticker_24h(self) -> pd.DataFrame:
        payload = self._request_json("/api/v3/ticker/24hr")
        rows: list[dict[str, object]] = []
        for item in payload:
            rows.append(
                {
                    "symbol": str(item.get("symbol", "")).upper(),
                    "volume_24h": item.get("quoteVolume"),
                    "last_price": item.get("lastPrice"),
                }
            )
        return pd.DataFrame(rows)

    def _request_json(self, path: str) -> Any:
        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.session.get(f"{self.base_url}{path}", timeout=self.timeout)
                response.raise_for_status()
                return response.json()
            except (requests.RequestException, ValueError) as exc:
                last_error = exc
                logger.warning(
                    "Binance universe request failed for %s on attempt %s/%s: %s",
                    path,
                    attempt,
                    self.max_retries,
                    exc,
                )
                if attempt < self.max_retries:
                    sleep(0.5 * attempt)
        raise RuntimeError(f"Failed to fetch Binance universe data from {path}") from last_error

    @staticmethod
    def _default_output_path(*, top: int) -> Path:
        if top == settings.auto_universe_top_n:
            return settings.auto_universe_path
        return settings.processed_data_dir / f"market_universe_top{int(top)}.csv"
