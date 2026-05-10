from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from alphascope.monitoring.healthcheck import HealthcheckService
from alphascope.monitoring.metrics import MetricsCollector
from alphascope.infrastructure.redis_client import InMemoryRedisClient


def _make_local_test_dir(name: str) -> Path:
    path = Path("data/runtime/test_multi_agent_prod") / f"{name}_{uuid4().hex}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_metrics_collector_renders_distinct_prometheus_series_by_labels() -> None:
    test_dir = _make_local_test_dir("metrics")
    collector = MetricsCollector(output_path=str(test_dir / "metrics.jsonl"))
    collector.emit("multi_agent_agent_confidence", 0.7, {"agent": "market_intelligence", "symbol": "BTCUSDT"})
    collector.emit("multi_agent_agent_confidence", 0.8, {"agent": "news_sentiment", "symbol": "BTCUSDT"})
    rendered = collector.render_prometheus()
    assert 'agent="market_intelligence"' in rendered
    assert 'agent="news_sentiment"' in rendered


def test_healthcheck_service_reports_multi_agent_runtime_files() -> None:
    test_dir = _make_local_test_dir("healthcheck")
    runtime_dir = test_dir / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    (runtime_dir / "multi_agent_runtime_status.json").write_text(json.dumps({"last_decision": "BUY"}), encoding="utf-8")
    (runtime_dir / "multi_agent_heartbeat.json").write_text(json.dumps({"status": "running"}), encoding="utf-8")
    (runtime_dir / "multi_agent_scheduler_status.json").write_text(json.dumps({"job_count": 2}), encoding="utf-8")

    from alphascope.config.settings import settings

    original_data_dir = settings.data_dir
    object.__setattr__(settings, "data_dir", test_dir)
    try:
        status = HealthcheckService(redis_client=InMemoryRedisClient()).status()
    finally:
        object.__setattr__(settings, "data_dir", original_data_dir)

    assert "multi_agent" in status
    assert isinstance(status["multi_agent"], dict)
    assert status["multi_agent"]["heartbeat"]["status"] == "running"
