"""Shared helpers for declarative CLI command registration and dispatch."""

from __future__ import annotations

import argparse
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CommandSpec:
    """Describes a CLI command parser."""

    name: str
    help: str
    configure: Callable[[argparse.ArgumentParser], None] | None = None


def register_command_specs(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
    specs: Sequence[CommandSpec],
) -> None:
    """Create subparsers from declarative command specifications."""
    for spec in specs:
        parser = subparsers.add_parser(spec.name, help=spec.help)
        if spec.configure is not None:
            spec.configure(parser)


def dispatch_command(
    command_name: str,
    handlers: Mapping[str, Callable[..., None]],
    /,
    **kwargs: Any,
) -> bool:
    """Dispatch a parsed command using a handler mapping."""
    handler = handlers.get(command_name)
    if handler is None:
        return False
    handler(**kwargs)
    return True
