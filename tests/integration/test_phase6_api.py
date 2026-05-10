from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

fastapi = pytest.importorskip("fastapi")
pytest.importorskip("starlette")
from fastapi.testclient import TestClient

from alphascope.api.api_server import app
from alphascope.automation.pipeline import AutomationPipeline


def _prepare_api_files() -> None:
    Path("data/processed/rankings").mkdir(parents=True, exist_ok=True)
    Path("data/processed/predictions").mkdir(parents=True, exist_ok=True)
    Path("data/processed/paper_trades").mkdir(parents=True, exist_ok=True)

    pd.DataFrame({"symbol": ["BTCUSDT"], "score_final": [0.8]}).to_csv("data/processed/rankings/ranking_api.csv", index=False)
    pd.DataFrame({"symbol": ["BTCUSDT"], "predicted_probability": [0.82]}).to_csv("data/processed/predictions/predictions_api.csv", index=False)
    pd.DataFrame({"trade_id": ["1"], "symbol": ["BTCUSDT"], "pnl": [10.0], "status": ["CLOSED"]}).to_csv("data/processed/paper_trades/trades.csv", index=False)
    Path("data/processed/paper_trades/portfolio_snapshot.json").write_text(json.dumps({"cash_balance": 1000.0, "equity": 1010.0, "open_positions": 1}), encoding="utf-8")


def test_api_endpoints(monkeypatch) -> None:
    _prepare_api_files()

    def fake_run_once(self):
        return {"status": "ok"}

    monkeypatch.setattr(AutomationPipeline, "run_once", fake_run_once)

    client = TestClient(app)
    headers = {"x-api-key": "alphascope-dev-secret"}
    assert client.get("/ranking", headers=headers).status_code == 200
    assert client.get("/portfolio", headers=headers).status_code == 200
    assert client.get("/trades", headers=headers).status_code == 200
    assert client.get("/signals", headers=headers).status_code == 200
    assert client.get("/health").status_code == 200
    assert client.get("/metrics", headers=headers).status_code == 200
    assert client.post("/pipeline/run", headers=headers).json() == {"status": "ok"}
