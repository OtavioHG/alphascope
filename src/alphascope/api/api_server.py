from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import Depends, FastAPI

from alphascope.automation.pipeline import AutomationPipeline
from alphascope.monitoring.metrics import MetricsCollector
from alphascope.security.api_keys import verify_api_key

app = FastAPI(title="AlphaScope API", version="1.0.0")


def _read_csv(path: str | Path) -> pd.DataFrame:
    file_path = Path(path)
    if not file_path.exists():
        return pd.DataFrame()
    return pd.read_csv(file_path)


def _read_json(path: str | Path) -> dict[str, Any]:
    file_path = Path(path)
    if not file_path.exists():
        return {}
    return json.loads(file_path.read_text(encoding="utf-8"))


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ranking")
def ranking(_: str = Depends(verify_api_key)) -> dict[str, Any]:
    frame = _read_csv("data/processed/rankings/ranking_api.csv")
    return {"latest": frame.to_dict(orient="records")}


@app.get("/portfolio")
def portfolio(_: str = Depends(verify_api_key)) -> dict[str, Any]:
    return _read_json("data/processed/paper_trades/portfolio_snapshot.json")


@app.get("/trades")
def trades(_: str = Depends(verify_api_key)) -> dict[str, Any]:
    frame = _read_csv("data/processed/paper_trades/trades.csv")
    return {"trades": frame.to_dict(orient="records")}


@app.get("/signals")
def signals(_: str = Depends(verify_api_key)) -> dict[str, Any]:
    frame = _read_csv("data/processed/predictions/predictions_api.csv")
    return {"signals": frame.to_dict(orient="records")}


@app.get("/metrics")
def metrics(_: str = Depends(verify_api_key)) -> str:
    return MetricsCollector().render_prometheus()


@app.post("/pipeline/run")
def run_pipeline(_: str = Depends(verify_api_key)) -> dict[str, Any]:
    return AutomationPipeline().run_once()
