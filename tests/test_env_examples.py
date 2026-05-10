from __future__ import annotations

from pathlib import Path


def _parse_env_example(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def test_root_env_example_uses_safe_defaults() -> None:
    values = _parse_env_example(Path(".env.example"))

    assert values["LIVE_TRADING_ENABLED"] == "false"
    assert values["LIVE_TRADING_MODE"] == "paper"
    assert values["LIVE_ALLOW_LIVE_MODE"] == "false"
    assert values["TELEGRAM_ENABLED"] == "false"
    assert values["ENABLE_TELEGRAM_ALERTS"] == "false"
    assert values["TELEGRAM_CHAT_ID"] == ""
    assert values["DATABASE_URL"] == "postgresql+psycopg://postgres:postgres@127.0.0.1:5432/alphascope"
    assert values["BINANCE_API_KEY"] == "your_binance_api_key_here"
    assert values["OPENROUTER_API_KEY"] == "your_openrouter_api_key_here"


def test_deployment_env_example_is_safe_by_default() -> None:
    values = _parse_env_example(Path("deployment/config/app.env.example"))

    assert values["LIVE_TRADING_MODE"] == "paper"
    assert values["LIVE_TRADING_ENABLED"] == "false"
    assert values["TELEGRAM_ENABLED"] == "false"
    assert values["ENABLE_TELEGRAM_ALERTS"] == "false"
    assert values["TELEGRAM_CHAT_ID"] == ""
    assert values["OPENROUTER_API_KEY"] == "your_openrouter_api_key_here"
