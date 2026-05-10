"""Fear and Greed Index client."""

from __future__ import annotations

from time import sleep
from typing import Any

import pandas as pd
import requests

from alphascope.config.settings import settings
from alphascope.core.logger import get_logger

logger = get_logger(__name__)


class FearGreedIndexClient:
    """Client for the Alternative.me Fear and Greed Index API."""

    def __init__(
        self,
        api_url: str | None = None,
        timeout: int | None = None,
        max_retries: int | None = None,
        session: requests.Session | None = None,
    ) -> None:
        self.api_url = api_url or settings.fear_greed_api_url
        self.timeout = timeout or settings.request_timeout
        self.max_retries = max_retries or settings.request_retries
        self.session = session or requests.Session()

    def fetch_fear_greed_index(self, *, limit: int = 30) -> pd.DataFrame:
        """Fetch recent Fear and Greed observations."""
        payload = self._request_json(params={"limit": int(limit), "format": "json"})
        frame = pd.DataFrame(payload.get("data", []))
        if frame.empty:
            return pd.DataFrame(columns=["timestamp", "fear_greed_value", "fear_greed_label"])
        frame["timestamp"] = pd.to_datetime(pd.to_numeric(frame["timestamp"], errors="coerce"), unit="s", utc=True)
        frame["fear_greed_value"] = pd.to_numeric(frame.get("value"), errors="coerce")
        frame["fear_greed_label"] = frame.get("value_classification", "").astype(str)
        return (
            frame.loc[:, ["timestamp", "fear_greed_value", "fear_greed_label"]]
            .dropna(subset=["timestamp", "fear_greed_value"])
            .drop_duplicates(subset=["timestamp"], keep="last")
            .sort_values("timestamp")
            .reset_index(drop=True)
        )

    def _request_json(self, params: dict[str, Any] | None = None) -> Any:
        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.session.get(self.api_url, params=params, timeout=self.timeout)
                response.raise_for_status()
                return response.json()
            except (requests.RequestException, ValueError) as exc:
                last_error = exc
                logger.warning("Fear & Greed request failed on attempt %s/%s: %s", attempt, self.max_retries, exc)
                if attempt < self.max_retries:
                    sleep(0.5 * attempt)
        raise RuntimeError("Fear & Greed request failed") from last_error
