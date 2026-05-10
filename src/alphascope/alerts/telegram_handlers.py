from __future__ import annotations

from typing import TYPE_CHECKING

from alphascope.alerts.telegram_command_templates import api_status_message, positions_message, risk_message
from alphascope.config.settings import settings

if TYPE_CHECKING:
    from alphascope.alerts.telegram_command_listener import TelegramCommandContext, TelegramCommandListener


def _start(listener: "TelegramCommandListener", context: "TelegramCommandContext", args: list[str]) -> str:
    del context, args
    return listener._welcome_message()


def _ping(listener: "TelegramCommandListener", context: "TelegramCommandContext", args: list[str]) -> str:
    del listener, context, args
    return "pong"


def _help(listener: "TelegramCommandListener", context: "TelegramCommandContext", args: list[str]) -> str:
    del context, args
    return listener._help_message()


def _status(listener: "TelegramCommandListener", context: "TelegramCommandContext", args: list[str]) -> str:
    del context, args
    return listener._status_message()


def _ma_status(listener: "TelegramCommandListener", context: "TelegramCommandContext", args: list[str]) -> str:
    del context, args
    return listener._multi_agent_status_message()


def _ma_last(listener: "TelegramCommandListener", context: "TelegramCommandContext", args: list[str]) -> str:
    del context, args
    return listener._multi_agent_last_decision_message()


def _ma_run(listener: "TelegramCommandListener", context: "TelegramCommandContext", args: list[str]) -> str:
    del context
    return listener._multi_agent_run(args)


def _positions(listener: "TelegramCommandListener", context: "TelegramCommandContext", args: list[str]) -> str:
    del context, args
    return positions_message(listener.repository.get_open_positions().to_dict(orient="records"))


def _ranking(listener: "TelegramCommandListener", context: "TelegramCommandContext", args: list[str]) -> str:
    del context, args
    return listener._ranking_message()


def _profit(listener: "TelegramCommandListener", context: "TelegramCommandContext", args: list[str]) -> str:
    del context, args
    return listener._profit_message()


def _portfolio(listener: "TelegramCommandListener", context: "TelegramCommandContext", args: list[str]) -> str:
    del context, args
    return listener._portfolio_message()


def _apis(listener: "TelegramCommandListener", context: "TelegramCommandContext", args: list[str]) -> str:
    del listener, context, args
    return api_status_message(settings.api_status_summary())


def _stopalerts(listener: "TelegramCommandListener", context: "TelegramCommandContext", args: list[str]) -> str:
    del context, args
    listener._set_runtime_alerts_enabled(False)
    return "Alertas Telegram desabilitados temporariamente."


def _startalerts(listener: "TelegramCommandListener", context: "TelegramCommandContext", args: list[str]) -> str:
    del context, args
    listener._set_runtime_alerts_enabled(True)
    return "Alertas Telegram reabilitados."


def _mode(listener: "TelegramCommandListener", context: "TelegramCommandContext", args: list[str]) -> str:
    del context, args
    return f"Modo atual: {listener.settings_manager.current_mode_label()}"


def _setmode(listener: "TelegramCommandListener", context: "TelegramCommandContext", args: list[str]) -> str:
    return listener._set_mode(args, context.chat_id)


def _symbols(listener: "TelegramCommandListener", context: "TelegramCommandContext", args: list[str]) -> str:
    del context, args
    return "Moedas monitoradas: " + ", ".join(listener._current_symbols())


def _addsymbol(listener: "TelegramCommandListener", context: "TelegramCommandContext", args: list[str]) -> str:
    del context
    return listener._add_symbol(args)


def _removesymbol(listener: "TelegramCommandListener", context: "TelegramCommandContext", args: list[str]) -> str:
    del context
    return listener._remove_symbol(args)


def _maxtrades(listener: "TelegramCommandListener", context: "TelegramCommandContext", args: list[str]) -> str:
    del listener, context, args
    return f"MAX_OPEN_TRADES atual: {settings.max_open_trades}"


def _setmaxtrades(listener: "TelegramCommandListener", context: "TelegramCommandContext", args: list[str]) -> str:
    del context
    return listener._set_max_trades(args)


def _risk(listener: "TelegramCommandListener", context: "TelegramCommandContext", args: list[str]) -> str:
    del context, args
    return risk_message(listener._risk_payload())


def _setrisk(listener: "TelegramCommandListener", context: "TelegramCommandContext", args: list[str]) -> str:
    return listener._set_risk(args, context.chat_id)


def _buy(listener: "TelegramCommandListener", context: "TelegramCommandContext", args: list[str]) -> str:
    del context
    return listener._buy(args)


def _sell(listener: "TelegramCommandListener", context: "TelegramCommandContext", args: list[str]) -> str:
    del context
    return listener._sell(args)


def _sellall(listener: "TelegramCommandListener", context: "TelegramCommandContext", args: list[str]) -> str:
    return listener._sell_all(args, context.chat_id)


def _restart(listener: "TelegramCommandListener", context: "TelegramCommandContext", args: list[str]) -> str:
    del context, args
    listener._offset = 0
    listener._bootstrapped = False
    listener._processed_ids.clear()
    listener._processed_lookup.clear()
    return "Listener Telegram reiniciado."


HANDLERS = {
    "/start": _start,
    "/ping": _ping,
    "/help": _help,
    "/status": _status,
    "/ma_status": _ma_status,
    "/ma_last": _ma_last,
    "/ma_run": _ma_run,
    "/positions": _positions,
    "/ranking": _ranking,
    "/profit": _profit,
    "/portfolio": _portfolio,
    "/apis": _apis,
    "/stopalerts": _stopalerts,
    "/startalerts": _startalerts,
    "/mode": _mode,
    "/setmode": _setmode,
    "/symbols": _symbols,
    "/addsymbol": _addsymbol,
    "/removesymbol": _removesymbol,
    "/maxtrades": _maxtrades,
    "/setmaxtrades": _setmaxtrades,
    "/risk": _risk,
    "/setrisk": _setrisk,
    "/buy": _buy,
    "/sell": _sell,
    "/sellall": _sellall,
    "/restart": _restart,
}
