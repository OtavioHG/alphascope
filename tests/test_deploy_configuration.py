from __future__ import annotations

from pathlib import Path

import yaml


def test_docker_compose_uses_supported_commands() -> None:
    compose_path = Path("docker-compose.yml")
    payload = yaml.safe_load(compose_path.read_text(encoding="utf-8"))
    services = payload["services"]
    assert "run-platform-api" in services["alphascope-api"]["command"]
    assert "run-dashboard" in services["alphascope-dashboard"]["command"]


def test_docker_compose_has_healthchecks() -> None:
    payload = yaml.safe_load(Path("docker-compose.yml").read_text(encoding="utf-8"))
    for service_name in ["alphascope-api", "alphascope-dashboard", "postgres", "redis"]:
        assert "healthcheck" in payload["services"][service_name], service_name
