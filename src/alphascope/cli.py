"""Command-line interface for AlphaScope V1."""

from __future__ import annotations

import argparse
import logging
from typing import Any

from alphascope.cli_data import add_data_ml_subparsers, handle_data_ml_command
from alphascope.cli_hierarchical import add_hierarchical_subparsers
from alphascope.cli_market import add_market_subparsers, handle_market_command
from alphascope.cli_metadata import COMMAND_PROFILES
from alphascope.cli_multi_agent import add_multi_agent_subparsers, handle_multi_agent_command
from alphascope.cli_platform import add_platform_subparsers, handle_platform_command
from alphascope.cli_runtime import add_runtime_subparsers, handle_runtime_command
from alphascope.config.settings import settings
from alphascope.core.logger import configure_logging
from alphascope.ui import print_error, print_header

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    """Build the AlphaScope CLI parser."""
    parser = argparse.ArgumentParser(prog="alphascope", description="AlphaScope V1 CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)
    add_hierarchical_subparsers(subparsers)
    add_market_subparsers(subparsers)
    add_runtime_subparsers(subparsers)
    add_data_ml_subparsers(subparsers)
    add_platform_subparsers(subparsers)
    add_multi_agent_subparsers(subparsers)

    return parser


def main() -> None:
    """Entry point for the AlphaScope CLI."""
    configure_logging()
    _log_api_configuration()
    args = build_parser().parse_args()
    if _command_needs_database(args.command):
        from alphascope.storage.database import init_database

        init_database()
    services = _build_services(args.command)

    print_header(_build_subtitle(args))

    try:
        if handle_market_command(
            args,
            pipeline=services.get("pipeline"),
            repository=services.get("repository"),
            aggregator=services.get("aggregator"),
            universe_builder=services.get("universe_builder"),
        ):
            pass
        elif handle_runtime_command(args, repository=services.get("repository")):
            pass
        elif handle_platform_command(args):
            pass
        elif handle_multi_agent_command(args):
            pass
        elif handle_data_ml_command(
            args,
            repository=services.get("repository"),
            pipeline=services.get("pipeline"),
        ):
            pass
        else:
            raise ValueError(f"Unsupported command: {args.command}")
    except Exception as exc:
        print_error(str(exc))
        raise SystemExit(1) from exc

def _build_subtitle(args: argparse.Namespace) -> str:
    command_label = str(args.command).replace("-", " ").title()
    return f"{command_label} | terminal interface"


def _log_api_configuration() -> None:
    for api_name, status in settings.api_status_summary().items():
        logger.info("API %s: %s", api_name, status)


def _command_needs_database(command: str) -> bool:
    profile = COMMAND_PROFILES.get(command)
    if profile is None:
        return True
    return profile.needs_database


def _build_services(command: str) -> dict[str, Any]:
    from alphascope.storage.repositories import StorageRepository

    profile = COMMAND_PROFILES.get(command)
    needs_repository = True if profile is None else profile.needs_repository
    services: dict[str, Any] = {"repository": StorageRepository() if needs_repository else None}

    needs_pipeline = False if profile is None else profile.needs_pipeline
    if not needs_pipeline:
        return services

    from alphascope.core.pipeline import AlphaScopePipeline

    services["pipeline"] = AlphaScopePipeline()

    if profile is not None and profile.needs_aggregator:
        from alphascope.external_data.aggregator import MarketDataAggregator

        services["aggregator"] = MarketDataAggregator()
    if profile is not None and profile.needs_universe_builder:
        from alphascope.universe.builder import BinanceUniverseBuilder

        services["universe_builder"] = BinanceUniverseBuilder()
    return services

if __name__ == "__main__":
    main()
