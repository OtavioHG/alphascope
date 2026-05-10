from __future__ import annotations

from datetime import UTC, datetime

try:
    from fastapi import FastAPI
    from fastapi.responses import PlainTextResponse
except Exception:  # pragma: no cover - optional runtime dependency
    FastAPI = None  # type: ignore[assignment]
    PlainTextResponse = None  # type: ignore[assignment]


def create_platform_api() -> FastAPI:
    if FastAPI is None:
        raise RuntimeError("FastAPI is not installed. Install requirements.txt to run the platform API.")
    from alphascope.config.settings import settings
    from alphascope.monitoring.healthcheck import HealthcheckService
    from alphascope.monitoring.metrics import MetricsCollector
    from alphascope.platform import AlphaPlatformService
    from alphascope.storage.repositories import StorageRepository

    app = FastAPI(title="AlphaScope Platform API", version="2.0.0")
    repository = StorageRepository()
    platform_service = AlphaPlatformService()

    @app.get("/healthz")
    def healthz() -> dict[str, object]:
        return {
            "timestamp": datetime.now(UTC).isoformat(),
            "service": "alphascope-platform-api",
            "health": HealthcheckService().status(),
        }

    @app.get("/healthz/multi-agent")
    def multi_agent_healthz() -> dict[str, object]:
        health = HealthcheckService().status()
        return {
            "timestamp": datetime.now(UTC).isoformat(),
            "service": "alphascope-platform-api",
            "multi_agent": health.get("multi_agent", {}),
            "multi_agent_tables": health.get("multi_agent_tables", False),
            "status": health.get("status", "degraded"),
        }

    @app.get("/dashboard")
    def dashboard() -> dict[str, object]:
        ranking = repository.get_latest_ranking(settings.default_interval)
        return {
            "account": repository.get_latest_account_snapshot(),
            "daily_performance": repository.get_daily_performance(),
            "positions": repository.get_open_positions().to_dict(orient="records"),
            "recent_orders": repository.get_trade_executions(limit=20).to_dict(orient="records"),
            "ranking": ranking.head(10).to_dict(orient="records"),
            "best_coin": None if ranking.empty else str(ranking.iloc[0]["symbol"]),
        }

    @app.get("/ranking")
    def ranking() -> dict[str, object]:
        return {
            "latest": repository.get_latest_ranking(settings.default_interval).to_dict(orient="records"),
            "history": repository.get_ranking_cycles(interval=settings.default_interval, limit=50).to_dict(orient="records"),
        }

    @app.get("/positions")
    def positions() -> dict[str, object]:
        return {"positions": repository.get_open_positions().to_dict(orient="records")}

    @app.get("/history")
    def history() -> dict[str, object]:
        return {"trades": repository.get_trade_executions(limit=100).to_dict(orient="records")}

    @app.get("/risk")
    def risk() -> dict[str, object]:
        return {
            "daily_performance": repository.get_daily_performance(),
            "risk_events": repository.get_risk_events(limit=100).to_dict(orient="records"),
            "config": platform_service.config.risk.model_dump(),
        }

    @app.get("/config")
    def config() -> dict[str, object]:
        return platform_service.config.model_dump(mode="json")

    @app.get("/audit")
    def audit() -> dict[str, object]:
        return {"events": repository.get_audit_events(limit=200).to_dict(orient="records")}

    @app.get("/metrics", response_class=PlainTextResponse)
    def metrics() -> str:
        return MetricsCollector().render_prometheus()

    @app.post("/entry/evaluate")
    def entry_evaluate(payload: dict[str, object]) -> dict[str, object]:
        return platform_service.evaluate_entry(payload)

    @app.post("/exit/evaluate")
    def exit_evaluate(payload: dict[str, object]) -> list[dict[str, object]]:
        return platform_service.evaluate_exit(payload)

    @app.post("/risk/evaluate")
    def risk_evaluate(payload: dict[str, object]) -> dict[str, object]:
        return platform_service.evaluate_risk(payload)

    @app.post("/orders/validate")
    def orders_validate(payload: dict[str, object]) -> dict[str, object]:
        intent = dict(payload.get("intent", {}))
        filters = dict(payload.get("filters", {}))
        return platform_service.validate_order(intent, filters)

    return app

app = create_platform_api() if FastAPI is not None else None
