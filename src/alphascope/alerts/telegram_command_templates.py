from __future__ import annotations

from typing import Any


def _fmt_number(value: object, digits: int = 2) -> str:
    try:
        return f"{float(value):,.{digits}f}"
    except (TypeError, ValueError):
        return "-"


def _fmt_pct(value: object, digits: int = 2) -> str:
    try:
        return f"{float(value) * 100:.{digits}f}%"
    except (TypeError, ValueError):
        return "-"


def _header(title: str, emoji: str) -> str:
    return f"{emoji} {title}"


def _line(label: str, value: object) -> str:
    return f"• {label}: {value if value not in (None, '') else '-'}"


def _section(title: str, lines: list[str]) -> list[str]:
    return [title, *lines]


def status_message(payload: dict[str, Any]) -> str:
    return "\n".join(
        [
            _header("Status operacional AlphaScope", "📊"),
            *_section(
                "Resumo",
                [
                    _line("APP_ENV", payload.get("app_env", "-")),
                    _line("Modo", payload.get("mode", "-")),
                    _line("Posições abertas", payload.get("open_positions", 0)),
                    _line("Trades abertos", payload.get("open_trades", 0)),
                    _line("Moedas monitoradas", payload.get("monitored_coins", 0)),
                ],
            ),
            "",
            *_section(
                "Telemetria",
                [
                    _line("Último ranking", payload.get("last_ranking", "-")),
                    _line("Último ciclo", payload.get("last_cycle", "-")),
                    _line("Telegram", payload.get("telegram_state", "-")),
                    _line("APIs", payload.get("api_state", "-")),
                ],
            ),
        ]
    )


def positions_message(positions: list[dict[str, Any]]) -> str:
    if not positions:
        return "💼 Nenhuma posição aberta no momento."
    lines = [_header("Posições abertas", "💼")]
    for item in positions:
        lines.extend(
            [
                f"• {item.get('symbol', '-')}",
                f"  qty={_fmt_number(item.get('quantity'), 6)} | entry={_fmt_number(item.get('entry_price'), 6)} | current={_fmt_number(item.get('current_price'), 6)}",
                f"  pnl={_fmt_number(item.get('unrealized_pnl'), 4)} | stop={_fmt_number(item.get('stop_price'), 6)} | tp={_fmt_number(item.get('take_profit_price'), 6)}",
            ]
        )
    return "\n".join(lines)


def ranking_message(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "📉 Ranking indisponível no momento."
    lines = [_header("Top ranking monitorado", "🏆")]
    for item in rows:
        lines.append(
            f"• #{item.get('rank', '-')} {item.get('symbol', '-')} | score={_fmt_number(item.get('score'), 4)} | tendência={item.get('trend', item.get('market_regime', '-'))}"
        )
    return "\n".join(lines)


def profit_message(payload: dict[str, Any]) -> str:
    return "\n".join(
        [
            _header("Resumo de resultado", "💰"),
            _line("Equity", _fmt_number(payload.get("equity"))),
            _line("Caixa", _fmt_number(payload.get("cash"))),
            _line("PnL realizado", _fmt_number(payload.get("realized_pnl"))),
            _line("PnL não realizado", _fmt_number(payload.get("unrealized_pnl"))),
            _line("Total de trades", payload.get("total_trades", 0)),
            _line("Win rate", _fmt_pct(payload.get("win_rate"))),
            _line("Drawdown", _fmt_pct(payload.get("drawdown"))),
        ]
    )


def api_status_message(payload: dict[str, str]) -> str:
    lines = [_header("Status das APIs", "🛰️")]
    for name, status in payload.items():
        lines.append(f"• {name}: {status}")
    return "\n".join(lines)


def risk_message(payload: dict[str, Any]) -> str:
    return "\n".join(
        [
            _header("Configuração de risco", "🛡️"),
            _line("MAX_POSITION_SIZE_PCT", _fmt_pct(payload.get("max_position_size_pct"))),
            _line("MAX_ACCOUNT_EXPOSURE_PCT", _fmt_pct(payload.get("max_account_exposure_pct"))),
            _line("MAX_DAILY_LOSS_PCT", _fmt_pct(payload.get("max_daily_loss_pct"))),
            _line("STOP_LOSS_PCT", _fmt_pct(payload.get("stop_loss_pct"))),
            _line("TAKE_PROFIT_PCT", _fmt_pct(payload.get("take_profit_pct"))),
            _line("TRAILING_STOP_PCT", _fmt_pct(payload.get("trailing_stop_pct"))),
        ]
    )


def portfolio_message(payload: dict[str, Any]) -> str:
    return "\n".join(
        [
            _header("Resumo de portfólio", "📦"),
            _line("Equity", _fmt_number(payload.get("equity"))),
            _line("Caixa", _fmt_number(payload.get("cash"))),
            _line("PnL realizado", _fmt_number(payload.get("realized_pnl"))),
            _line("PnL não realizado", _fmt_number(payload.get("unrealized_pnl"))),
            _line("Posições abertas", payload.get("open_positions", 0)),
            _line("Exposição", _fmt_pct(payload.get("exposure_pct"))),
        ]
    )


def multi_agent_status_message(payload: dict[str, Any]) -> str:
    lines = [
        _header("Status multiagente", "🤖"),
        _line("Último símbolo", payload.get("last_symbol", "-")),
        _line("Último timeframe", payload.get("last_timeframe", "-")),
        _line("Decisão", payload.get("last_decision", "-")),
        _line("Score final", _fmt_number(payload.get("last_score"), 4)),
        _line("Cache backend", payload.get("cache_backend", "-")),
        _line("Heartbeat", payload.get("heartbeat_status", "-")),
        _line("Jobs do scheduler", payload.get("scheduler_jobs", 0)),
        _line("Atualizado em", payload.get("updated_at", "-")),
    ]
    symbols = payload.get("symbols_summary") or []
    if symbols:
        lines.append("")
        lines.append("Últimos símbolos analisados")
        for item in symbols[:5]:
            lines.append(
                f"• {item.get('symbol', '-')} | decisão={item.get('decision', '-')} | score={_fmt_number(item.get('final_score'), 4)} | execução={item.get('execution_action', '-')}"
            )
    return "\n".join(lines)


def multi_agent_decision_message(payload: dict[str, Any]) -> str:
    return "\n".join(
        [
            _header("Última decisão multiagente", "🧠"),
            _line("Símbolo", payload.get("symbol", "-")),
            _line("Timeframe", payload.get("timeframe", "-")),
            _line("Decisão", payload.get("decision", "-")),
            _line("Score final", _fmt_number(payload.get("final_score"), 4)),
            _line("Consenso", payload.get("consensus", "-")),
            _line("Execução", payload.get("execution_action", "-")),
            _line("Justificativa", payload.get("reasoning", "-")),
        ]
    )
