"""Base abstractions for external market data providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, datetime
from time import sleep
from typing import Any

import pandas as pd
import requests

from alphascope.config.settings import settings
from alphascope.core.logger import get_logger
from alphascope.external_data.schemas import SourceHealthStatus


class ExternalMarketSource(ABC):
    """Base class for external market data providers."""

    source_name = "unknown"

    def __init__(
        self,
        base_url: str,
        timeout: int | None = None,
        max_retries: int | None = None,
        session: requests.Session | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout or settings.request_timeout
        self.max_retries = max_retries or settings.request_retries
        self.session = session or requests.Session()
        self.logger = get_logger(f"{__name__}.{self.source_name}")

    @abstractmethod
    def fetch_market_snapshot(self, limit: int = 250) -> pd.DataFrame:
        """Fetch a normalized market snapshot."""

    @abstractmethod
    def fetch_supported_assets(self, limit: int = 500) -> pd.DataFrame:
        """Fetch the supported asset universe for the source."""

    def healthcheck(self) -> SourceHealthStatus:
        """Check whether the remote source is responding."""
        try:
            self.fetch_market_snapshot(limit=1)
            return SourceHealthStatus(
                source=self.source_name,
                available=True,
                checked_at=datetime.now(UTC),
                detail="ok",
            )
        except Exception as exc:
            return SourceHealthStatus(
                source=self.source_name,
                available=False,
                checked_at=datetime.now(UTC),
                detail=str(exc),
            )

    def _request_json(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> Any:
        """Perform a GET request with simple retry handling."""
        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.session.get(
                    f"{self.base_url}{path}",
                    params=params,
                    headers=headers,
                    timeout=self.timeout,
                )
                response.raise_for_status()
                return response.json()
            except (requests.RequestException, ValueError) as exc:
                last_error = exc
                self.logger.warning(
                    "Request failed for %s%s on attempt %s/%s: %s",
                    self.base_url,
                    path,
                    attempt,
                    self.max_retries,
                    exc,
                )
                if attempt < self.max_retries:
                    sleep(0.5 * attempt)
        raise RuntimeError(f"External request failed for source {self.source_name}") from last_error
