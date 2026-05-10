from __future__ import annotations

from alphascope.automation.scheduler import AutomationScheduler
from alphascope.cli import build_parser
from alphascope.config.settings import settings
from alphascope.execution.trader_selector import selected_trader_name
from alphascope.runtime_validation import RuntimeValidator


class DummyPipeline:
    def refresh_market(self):
        return None

    def refresh_news(self):
        return None

    def build_features(self):
        return None

    def build_ranking(self):
        return None

    def run_trading_cycle(self):
        return None


def test_scheduler_registers_modern_trading_job() -> None:
    scheduler = AutomationScheduler()
    scheduler.register_pipeline_jobs(DummyPipeline(), market_interval_seconds=5, news_interval_seconds=5, feature_interval_seconds=5, ranking_interval_seconds=5, paper_trading_interval_seconds=5)
    job_names = {job["name"] for job in scheduler.list_jobs()}
    assert "paper_trading_job" in job_names


def test_cli_includes_runtime_and_dashboard_commands() -> None:
    parser = build_parser()
    actions = [action for action in parser._actions if getattr(action, "choices", None)]
    commands = set()
    for action in actions:
        commands.update(action.choices.keys())
    assert "doctor" in commands
    assert "backup-db" in commands
    assert "verify-exchange-credentials" in commands
    assert "run-dashboard" in commands
    assert "train-production-ai" in commands


def test_runtime_validator_serializes_slot_dataclasses() -> None:
    result = RuntimeValidator().run()
    assert isinstance(result["checks"], list)
    assert result["checks"]
    first = result["checks"][0]
    assert isinstance(first, dict)
    assert {"name", "ok", "detail", "severity"}.issubset(first.keys())


def test_trader_selection_defaults_to_paper() -> None:
    original_enabled = settings.live_trading_enabled
    original_mode = settings.live_trading_mode
    try:
        object.__setattr__(settings, "live_trading_enabled", False)
        object.__setattr__(settings, "live_trading_mode", "paper")
        assert selected_trader_name() == "PaperTrader"
    finally:
        object.__setattr__(settings, "live_trading_enabled", original_enabled)
        object.__setattr__(settings, "live_trading_mode", original_mode)
