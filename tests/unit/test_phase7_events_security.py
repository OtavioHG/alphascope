from __future__ import annotations

import pytest

from alphascope.events.event_bus import EventBus
from alphascope.events.event_types import Event, MARKET_DATA_UPDATED

fastapi = pytest.importorskip("fastapi")
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient

from alphascope.security.auth import create_jwt_token
from alphascope.security.api_keys import verify_api_key
from alphascope.security.rate_limit import RateLimiter


def test_event_bus_publishes_and_dispatches() -> None:
    captured: list[dict] = []
    bus = EventBus()
    bus.subscribe(MARKET_DATA_UPDATED, lambda event: captured.append(event.payload))

    bus.publish(Event(MARKET_DATA_UPDATED, {"symbol": "BTCUSDT"}))

    assert captured == [{"symbol": "BTCUSDT"}]
    assert bus.messages(MARKET_DATA_UPDATED)[0]["payload"]["symbol"] == "BTCUSDT"


def test_rate_limiter_blocks_after_limit() -> None:
    limiter = RateLimiter(limit=2, window_seconds=60)
    limiter.check("client-a")
    limiter.check("client-a")
    with pytest.raises(Exception):
        limiter.check("client-a")


def test_api_key_and_bearer_helpers_work() -> None:
    app = FastAPI()

    @app.get("/secure")
    def secure(_: str = Depends(verify_api_key)):
        return {"status": "ok"}

    client = TestClient(app)
    assert client.get("/secure").status_code == 401
    assert client.get("/secure", headers={"x-api-key": "alphascope-dev-secret"}).json() == {"status": "ok"}

    token = create_jwt_token("tester")
    assert isinstance(token, str)
    assert "." in token
