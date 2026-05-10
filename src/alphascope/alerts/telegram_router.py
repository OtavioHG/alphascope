from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from alphascope.alerts.telegram_command_listener import TelegramCommandContext, TelegramCommandListener


@dataclass(frozen=True, slots=True)
class ParsedTelegramCommand:
    name: str
    args: list[str]


TelegramHandler = Callable[["TelegramCommandListener", "TelegramCommandContext", list[str]], str]


def parse_command(text: str) -> ParsedTelegramCommand:
    parts = text.split()
    if not parts:
        return ParsedTelegramCommand(name="", args=[])
    return ParsedTelegramCommand(name=parts[0].lower(), args=parts[1:])


def dispatch_command(listener: "TelegramCommandListener", context: "TelegramCommandContext") -> str:
    from alphascope.alerts.telegram_handlers import HANDLERS

    parsed = parse_command(context.text)
    handler = HANDLERS.get(parsed.name)
    if handler is None:
        return "Comando desconhecido. Use /help."
    return handler(listener, context, parsed.args)
