from __future__ import annotations

import pandas as pd

from alphascope.ingestion.binance_client import BinanceClient
from alphascope.ingestion.market_ingestor import MarketIngestor


class DummyResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self):
        return self._payload


class DummySession:
    def __init__(self, payload):
        self.payload = payload

    def get(self, *args, **kwargs):
        return DummyResponse(self.payload)


def test_binance_client_normalizes_klines():
    payload = [
        [1704067200000, "100", "110", "95", "105", "1500", 1704070799999, "0", "0", "0", "0", "0"],
        [1704070800000, "105", "115", "100", "112", "1800", 1704074399999, "0", "0", "0", "0", "0"],
    ]
    client = BinanceClient(session=DummySession(payload), max_retries=1)

    frame = client.fetch_klines("BTCUSDT", "1h", 2)

    assert list(frame.columns) == ["timestamp", "open", "high", "low", "close", "volume", "symbol", "interval"]
    assert len(frame) == 2
    assert frame["symbol"].iloc[0] == "BTCUSDT"
    assert str(frame["timestamp"].dtype).startswith("datetime64")


def test_market_ingestor_fetch_ohlcv_compatibility():
    payload = [
        [1704067200000, "100", "110", "95", "105", "1500", 1704070799999, "0", "0", "0", "0", "0"],
    ]
    ingestor = MarketIngestor(client=BinanceClient(session=DummySession(payload), max_retries=1))

    rows = ingestor.fetch_ohlcv("BTCUSDT", "1h", 1)

    assert rows == [[1704067200000, 100.0, 110.0, 95.0, 105.0, 1500.0]]
