from __future__ import annotations

import requests

from alphascope.ingestion.binance_client import BinanceClient


class DummyResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self):
        return self._payload


class RetrySession:
    def __init__(self, payload):
        self.payload = payload
        self.calls = 0

    def get(self, *args, **kwargs):
        self.calls += 1
        if self.calls == 1:
            raise requests.Timeout("timeout")
        return DummyResponse(self.payload)


def test_get_klines_normalizes_payload_and_retries():
    payload = [
        [1704067200000, "10", "11", "9", "10.5", "150", 1704070799999, "0", "0", "0", "0", "0"],
        [1704070800000, "10.5", "12", "10", "11.5", "175", 1704074399999, "0", "0", "0", "0", "0"],
    ]
    session = RetrySession(payload)

    frame = BinanceClient(session=session, max_retries=2, timeout=1).get_klines("BTCUSDT", "1h", 2)

    assert session.calls == 2
    assert list(frame.columns) == ["timestamp", "open", "high", "low", "close", "volume", "symbol", "interval"]
    assert frame["close"].tolist() == [10.5, 11.5]
    assert frame["symbol"].unique().tolist() == ["BTCUSDT"]
