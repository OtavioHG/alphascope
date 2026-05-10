"""Client for fetching news from the GDELT API."""

from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta

import pandas as pd
import requests
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

from alphascope.config.settings import settings
from alphascope.core.logger import get_logger

logger = get_logger(__name__)


class GDELTNewsClient:
    """Fetch news articles from the public GDELT document API."""

    def __init__(self, base_url: str | None = None, timeout: int | None = None) -> None:
        self.base_url = (base_url or settings.gdelt_base_url).rstrip("/")
        self.timeout = timeout or settings.request_timeout
        self._cache = {}
        self._cache_ttl = 1800  # 30 minutes
        
        # Setup resilient session
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "AlphaScope/1.0 (Quant System; Research; +https://github.com/alphascope)",
            "Accept": "application/json",
        })
        
        retry_strategy = Retry(
            total=3,
            backoff_factor=2,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        logger.info("GDELT news client configured for %s with retries and cache", self.base_url)

    def fetch_articles(self, query: str, *, max_records: int = 50, days: int = 1) -> pd.DataFrame:
        """Fetch recent articles for the supplied query with high resilience."""
        query = self._normalize_query(query)
        cache_key = f"{query}_{days}_{max_records}"
        cached_result, timestamp = self._cache.get(cache_key, (None, 0))
        
        if cached_result is not None and (time.time() - timestamp) < self._cache_ttl:
            logger.info("Using cached GDELT result for query: %s", query)
            return cached_result.copy()

        end = datetime.now(UTC)
        start = end - timedelta(days=days)
        
        params = {
            "query": query,
            "mode": "artlist",
            "maxrecords": max_records,
            "format": "json",
            "startdatetime": start.strftime("%Y%m%d%H%M%S"),
            "enddatetime": end.strftime("%Y%m%d%H%M%S"),
        }

        try:
            logger.info("Fetching GDELT news for: %s (limit=%d, days=%d)", query, max_records, days)
            response = self.session.get(
                f"{self.base_url}/api/v2/doc/doc",
                params=params,
                timeout=(10, 30),
            )
            
            # 1. Check for basic HTTP errors (after retries)
            response.raise_for_status()
            
            # 2. Check for empty response body
            if not response.text or not response.text.strip():
                logger.warning("GDELT returned empty response body")
                return pd.DataFrame()

            # 3. Parse JSON safely
            try:
                data = response.json()
            except requests.exceptions.JSONDecodeError as e:
                logger.error("GDELT JSON decode failed: %s | Raw: %s", e, response.text[:200])
                return pd.DataFrame()
            except ValueError as e:
                logger.error("GDELT Value error during JSON parsing: %s", e)
                return pd.DataFrame()

            # 4. Validate GDELT specific structure
            if "articles" not in data:
                logger.warning("GDELT response missing 'articles' field")
                return pd.DataFrame()
            
            articles = data["articles"]
            if not isinstance(articles, list):
                logger.warning("GDELT 'articles' field is not a list: %s", type(articles))
                return pd.DataFrame()

            if not articles:
                logger.info("GDELT returned no articles for query: %s", query)
                frame = pd.DataFrame()
            else:
                frame = pd.DataFrame(articles)

            # 5. Process and format results
            if frame.empty:
                self._cache[cache_key] = (frame, time.time())
                return frame

            frame = self._process_frame(frame)
            
            # Cache the successful (or empty) result
            self._cache[cache_key] = (frame, time.time())
            return frame

        except requests.exceptions.ConnectTimeout:
            logger.error("GDELT connection timeout")
        except requests.exceptions.ReadTimeout:
            logger.error("GDELT read timeout")
        except requests.exceptions.ConnectionError as e:
            logger.error("GDELT connection error: %s", e)
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 429:
                logger.error("GDELT rate limited (429)")
            else:
                logger.error("GDELT HTTP error: %s", e)
        except Exception as e:
            logger.error("Unexpected error fetching GDELT news: %s", e, exc_info=True)

        return pd.DataFrame()

    def _process_frame(self, frame: pd.DataFrame) -> pd.DataFrame:
        """Normalize and filter GDELT dataframe."""
        frame = frame.rename(
            columns={
                "title": "title",
                "seendate": "timestamp",
                "socialimage": "description",
                "domain": "source",
                "url": "link",
            }
        )
        if "description" not in frame.columns:
            frame["description"] = ""
        frame["description"] = frame["description"].fillna("")
        frame["text"] = frame["description"]
        if "source" not in frame.columns:
            frame["source"] = None
        if "link" not in frame.columns:
            frame["link"] = None
        frame["dataset_source"] = "gdelt"
        
        columns = ["title", "description", "text", "timestamp", "source", "link", "dataset_source"]
        valid_cols = [col for col in columns if col in frame.columns]
        return frame.loc[:, valid_cols].drop_duplicates().reset_index(drop=True)

    @staticmethod
    def _normalize_query(query: str) -> str:
        normalized = str(query or "").strip()
        if not normalized:
            return normalized
        upper = normalized.upper()
        if " OR " in upper and not (normalized.startswith("(") and normalized.endswith(")")):
            return f"({normalized})"
        return normalized
