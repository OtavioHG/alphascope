from __future__ import annotations

import pytest


@pytest.mark.skipif(__import__('importlib').util.find_spec('fastapi') is None, reason='fastapi not installed')
def test_platform_api_exposes_multi_agent_health_and_metrics_endpoints() -> None:
    from fastapi.testclient import TestClient
    from alphascope.api.platform_api import create_platform_api

    app = create_platform_api()
    client = TestClient(app)

    health_response = client.get('/healthz/multi-agent')
    metrics_response = client.get('/metrics')

    assert health_response.status_code == 200
    body = health_response.json()
    assert 'multi_agent' in body
    assert 'multi_agent_tables' in body
    assert metrics_response.status_code == 200
