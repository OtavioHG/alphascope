from __future__ import annotations

from fastapi import Depends, FastAPI
from fastapi.responses import PlainTextResponse

from alphascope.api.routes.portfolio import router as portfolio_router
from alphascope.api.routes.ranking import router as ranking_router
from alphascope.api.routes.signals import router as signals_router
from alphascope.api.routes.trades import router as trades_router
from alphascope.automation.pipeline import AutomationPipeline
from alphascope.monitoring.healthcheck import HealthcheckService
from alphascope.monitoring.metrics import MetricsCollector
from alphascope.security.api_keys import verify_api_key
from alphascope.security.rate_limit import rate_limit_dependency

app = FastAPI(title="AlphaScope API", version="0.1.0")
app.include_router(ranking_router)
app.include_router(portfolio_router)
app.include_router(trades_router)
app.include_router(signals_router)


@app.post("/pipeline/run")
def run_pipeline(
    _: str = Depends(verify_api_key),
    __: None = Depends(rate_limit_dependency(limit=20, window_seconds=60)),
):
    return AutomationPipeline().run_once()


@app.get("/health")
def health():
    return HealthcheckService().status()


@app.get("/metrics", response_class=PlainTextResponse)
def metrics(
    _: str = Depends(verify_api_key),
    __: None = Depends(rate_limit_dependency()),
):
    return MetricsCollector().render_prometheus()
