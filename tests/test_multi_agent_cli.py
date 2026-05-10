from __future__ import annotations

from pathlib import Path

from alphascope.cli import build_parser


def test_cli_includes_multi_agent_commands() -> None:
    parser = build_parser()
    actions = [action for action in parser._actions if getattr(action, "choices", None)]
    commands: set[str] = set()
    for action in actions:
        commands.update(action.choices.keys())
    assert "run-multi-agent" in commands
    assert "run-debate" in commands
    assert "show-agent-output" in commands
    assert "show-consensus-history" in commands
    assert "run-supervisor" in commands
    assert "show-agent-performance" in commands
    assert "compare-agent-decisions" in commands
    assert "run-live-multi-agent" in commands
    assert "schedule-live-multi-agent" in commands
    assert "multi-agent-runtime-status" in commands
    assert "train-multi-agent-models" in commands
    assert "backtest-multi-agent" in commands
