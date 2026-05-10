from __future__ import annotations

from alphascope.cli import build_parser


def test_hierarchical_market_command_maps_to_legacy_command() -> None:
    parser = build_parser()
    args = parser.parse_args(["market", "pipeline", "run", "--symbols", "BTCUSDT"])

    assert args.command == "run-pipeline"
    assert args.symbols == "BTCUSDT"


def test_hierarchical_platform_api_command_maps_to_legacy_command() -> None:
    parser = build_parser()
    args = parser.parse_args(["platform", "api", "run", "--host", "127.0.0.1", "--port", "8010"])

    assert args.command == "run-platform-api"
    assert args.host == "127.0.0.1"
    assert args.port == 8010


def test_hierarchical_agents_live_schedule_maps_to_legacy_command() -> None:
    parser = build_parser()
    args = parser.parse_args(["agents", "live", "schedule", "--symbols", "BTCUSDT,ETHUSDT", "--interval", "1h"])

    assert args.command == "schedule-live-multi-agent"
    assert args.symbols == "BTCUSDT,ETHUSDT"
    assert args.interval == "1h"
