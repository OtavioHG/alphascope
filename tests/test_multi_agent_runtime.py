from __future__ import annotations

from pathlib import Path

from alphascope.agents.cache import MultiAgentCacheService
from alphascope.agents.runtime import MultiAgentRuntime
from alphascope.infrastructure.redis_client import InMemoryRedisClient


def test_multi_agent_cache_service_roundtrip() -> None:
    client = InMemoryRedisClient()
    client.flushall()
    cache = MultiAgentCacheService(client=client)
    cache.cache_context("BTCUSDT", "1h", {"symbol": "BTCUSDT", "mode": "paper"})
    cache.cache_result("BTCUSDT", "1h", {"decision": "BUY", "final_score": 0.8})
    cache.write_heartbeat({"component": "multi_agent", "status": "running"})

    context = cache.get_json("context:BTCUSDT:1h")
    result = cache.get_json("result:BTCUSDT:1h")
    status = cache.read_status()

    assert context is not None and context["symbol"] == "BTCUSDT"
    assert result is not None and result["decision"] == "BUY"
    assert status["heartbeat"]["component"] == "multi_agent"


def test_multi_agent_runtime_merges_status_by_symbol() -> None:
    test_dir = Path("data/runtime/test_multi_agent_runtime")
    test_dir.mkdir(parents=True, exist_ok=True)
    runtime = object.__new__(MultiAgentRuntime)
    runtime.status_path = test_dir / "multi_agent_runtime_status.json"
    if runtime.status_path.exists():
        runtime.status_path.unlink()

    MultiAgentRuntime._write_status(runtime, {"symbols": {"BTCUSDT": {"symbol": "BTCUSDT", "decision": "BUY", "updated_at": "2026-01-01T00:00:00+00:00"}}})
    MultiAgentRuntime._write_status(runtime, {"symbols": {"ETHUSDT": {"symbol": "ETHUSDT", "decision": "HOLD", "updated_at": "2026-01-01T00:05:00+00:00"}}})

    payload = runtime.status_path.read_text(encoding="utf-8")
    assert '"BTCUSDT"' in payload
    assert '"ETHUSDT"' in payload
