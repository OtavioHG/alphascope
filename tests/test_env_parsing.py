from __future__ import annotations

import importlib
import os


def test_settings_reload_respects_safe_live_defaults(monkeypatch) -> None:
    monkeypatch.setenv("LIVE_TRADING_ENABLED", "false")
    monkeypatch.setenv("LIVE_TRADING_MODE", "paper")
    monkeypatch.setenv("LIVE_ALLOW_LIVE_MODE", "false")
    monkeypatch.setenv("LLM_ENABLE_EXTERNAL", "true")
    monkeypatch.setenv("LLM_FORCE_LOCAL_FALLBACK", "true")
    monkeypatch.setenv("MARKET_AGENT_MODEL", "nvidia/nemotron-3-super-120b-a12b:free")
    monkeypatch.setenv("NEWS_AGENT_MODEL", "openai/gpt-oss-120b:free")
    monkeypatch.setenv("RISK_AGENT_MODEL", "minimax/minimax-m2.5:free")
    monkeypatch.setenv("MEMORY_AGENT_MODEL", "arcee-ai/trinity-large-preview:free")
    module = importlib.import_module("alphascope.config.settings")
    module = importlib.reload(module)

    assert module.settings.live_trading_enabled is False
    assert module.settings.live_trading_mode == "paper"
    assert module.settings.live_allow_live_mode is False
    assert module.settings.log_format in {"plain", "json"}
    assert module.settings.market_agent_model == "nvidia/nemotron-3-super-120b-a12b:free"
    assert module.settings.news_agent_model == "openai/gpt-oss-120b:free"
    assert module.settings.risk_agent_model == "minimax/minimax-m2.5:free"
    assert module.settings.memory_agent_model == "arcee-ai/trinity-large-preview:free"
    assert module.settings.external_llm_available is False


def test_settings_reload_blocks_live_mode_without_explicit_guard(monkeypatch) -> None:
    monkeypatch.setenv("LIVE_TRADING_ENABLED", "true")
    monkeypatch.setenv("LIVE_TRADING_MODE", "live")
    monkeypatch.setenv("LIVE_ALLOW_LIVE_MODE", "false")
    monkeypatch.setenv("API_KEY_SECRET", "dev-secret")
    monkeypatch.setenv("JWT_SECRET", "dev-secret")

    settings_module = importlib.import_module("alphascope.config.settings")
    try:
        importlib.reload(settings_module)
    except RuntimeError as exc:
        assert "LIVE_ALLOW_LIVE_MODE=true" in str(exc)
    else:
        raise AssertionError("Expected RuntimeError when live mode is enabled without explicit guard")
    finally:
        monkeypatch.setenv("LIVE_TRADING_ENABLED", "false")
        monkeypatch.setenv("LIVE_TRADING_MODE", "paper")
        importlib.reload(settings_module)
