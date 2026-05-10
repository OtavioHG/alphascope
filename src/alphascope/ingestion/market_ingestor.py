"""Market ingestion orchestration."""

from __future__ import annotations

import pandas as pd

from alphascope.core.logger import get_logger
from alphascope.ingestion.binance_client import BinanceClient
from alphascope.ingestion.schemas import IngestionRequest, IngestionResult
from alphascope.storage.repositories import StorageRepository

logger = get_logger(__name__)


class MarketIngestor:
    """Fetch and persist market candles for one or many assets."""

    def __init__(self, client: BinanceClient | None = None, repository: StorageRepository | None = None) -> None:
        self.client = client or BinanceClient()
        self.repository = repository or StorageRepository()

    def fetch_ohlcv(self, symbol: str, interval: str, limit: int) -> list[list[float | int]]:
        frame = self.client.get_klines(symbol, interval, limit)
        rows: list[list[float | int]] = []
        for row in frame.itertuples(index=False):
            rows.append([
                int(pd.Timestamp(row.timestamp).timestamp() * 1000),
                float(row.open),
                float(row.high),
                float(row.low),
                float(row.close),
                float(row.volume),
            ])
        return rows

    def ingest(self, symbols: list[str], intervals: list[str], limit: int) -> list[IngestionResult]:
        results: list[IngestionResult] = []
        for symbol in symbols:
            for interval in intervals:
                request = IngestionRequest(symbol=symbol, interval=interval, limit=limit)
                frame = self.client.get_klines(request.symbol, request.interval, request.limit)
                inserted = self.repository.save_candles(frame)
                logger.info("Persisted %s candle rows for %s %s", inserted, symbol, interval)
                results.append(IngestionResult(symbol=symbol, interval=interval, rows=inserted, frame=frame))
        return results

    def load(self, symbol: str, interval: str, limit: int | None = None) -> pd.DataFrame:
        return self.repository.get_candles(symbol=symbol, interval=interval, limit=limit)
