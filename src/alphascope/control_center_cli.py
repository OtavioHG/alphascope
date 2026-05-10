from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from alphascope.config.settings import settings
from alphascope.platform import AlphaPlatformService, AuditService
from alphascope.storage.repositories import StorageRepository
from alphascope.textual_app import create_control_center_app

try:
    import typer
except Exception:  # pragma: no cover - fallback for minimal environments
    typer = None


console = Console()
app = typer.Typer(help="AlphaScope professional control center") if typer else None


def _safe_system_metrics() -> dict[str, float]:
    try:
        import psutil

        return {
            "cpu_pct": float(psutil.cpu_percent(interval=0.05)),
            "memory_pct": float(psutil.virtual_memory().percent),
        }
    except Exception:
        return {"cpu_pct": 0.0, "memory_pct": 0.0}


def render_dashboard(repository: StorageRepository | None = None) -> None:
    repository = repository or StorageRepository()
    snapshot = repository.get_latest_account_snapshot() or {}
    daily = repository.get_daily_performance() or {}
    ranking = repository.get_latest_ranking(settings.default_interval)
    positions = repository.get_open_positions()
    trades = repository.get_trade_executions(limit=10)
    metrics = _safe_system_metrics()
    best_coin = str(ranking.iloc[0]["symbol"]) if not ranking.empty else "-"
    regime = str(ranking.iloc[0]["market_regime"]) if not ranking.empty else "unknown"

    hero = Panel.fit(
        "\n".join(
            [
                "AlphaScope Control Center",
                "Quantitative Crypto Terminal v2",
                "",
                f"Portfolio Value : ${snapshot.get('total_balance', 0.0):.2f}",
                f"Available Cash : ${snapshot.get('free_balance', 0.0):.2f}",
                f"Open Positions  : {snapshot.get('open_positions', 0)}",
                f"Daily PnL       : {daily.get('realized_pnl_pct', 0.0):+.2%}",
                f"Win Rate        : {daily.get('win_rate', 0.0):.2%}",
                f"Market Regime   : {regime}",
                f"Bot Status      : {'RUNNING' if not daily.get('paused', False) else 'PAUSED'}",
            ]
        ),
        border_style="green",
    )
    console.print(hero)

    menu = Table(title="Main Menu", show_header=False)
    menu.add_column("Option")
    menu.add_column("Label")
    rows = [
        ("[1]", "Dashboard"),
        ("[2]", "Open Positions"),
        ("[3]", "Rankings"),
        ("[4]", "Trading History"),
        ("[5]", "Risk Management"),
        ("[6]", "Strategy Settings"),
        ("[7]", "Telegram Settings"),
        ("[8]", "API Management"),
        ("[9]", "Logs and Errors"),
        ("[10]", "Backtesting"),
        ("[11]", "Model Training"),
        ("[12]", "Market Scanner"),
        ("[13]", "Start Bot"),
        ("[14]", "Stop Bot"),
        ("[15]", "Emergency Sell All"),
        ("[16]", "Exit"),
    ]
    for row in rows:
        menu.add_row(*row)
    console.print(menu)

    summary = Table(title="Live Metrics")
    summary.add_column("Metric")
    summary.add_column("Value")
    summary.add_row("PnL diário", f"{daily.get('realized_pnl_pct', 0.0):+.2%}")
    summary.add_row("Drawdown", f"{daily.get('max_drawdown', 0.0):.2%}")
    summary.add_row("Win rate", f"{daily.get('win_rate', 0.0):.2%}")
    summary.add_row("Melhor moeda do dia", best_coin)
    summary.add_row("CPU", f"{metrics['cpu_pct']:.1f}%")
    summary.add_row("Memória", f"{metrics['memory_pct']:.1f}%")
    summary.add_row("Posições abertas", str(len(positions)))
    summary.add_row("Ordens recentes", str(len(trades)))
    console.print(summary)


def render_status() -> None:
    repository = StorageRepository()
    service = AlphaPlatformService()
    console.print(
        {
            "timestamp": datetime.now(UTC).isoformat(),
            "risk_profile": service.config.risk.profile.value,
            "daily_performance": repository.get_daily_performance(),
            "account": repository.get_latest_account_snapshot(),
            "open_positions": repository.get_open_positions().to_dict(orient="records"),
        }
    )


def run_tui() -> None:
    app_instance = create_control_center_app()
    app_instance.run()


def evaluate_entry(payload: dict[str, Any]) -> None:
    result = AlphaPlatformService().evaluate_entry(payload)
    console.print(result)


def _record_audit(action: str, source: str) -> None:
    AuditService().record(action, actor="operator", source=source, target="control_center")


if app:
    @app.command("dashboard")
    def dashboard_command() -> None:
        _record_audit("dashboard_opened", "cli")
        render_dashboard()

    @app.command("status")
    def status_command() -> None:
        render_status()

    @app.command("tui")
    def tui_command() -> None:
        _record_audit("control_center_tui", "cli")
        run_tui()

    @app.command("entry-check")
    def entry_check_command(
        symbol: str,
        close: float,
        rsi: float,
        macd_histogram: float,
        ma_fast: float,
        ma_slow: float,
        trend_strength: float,
        relative_volume: float,
        volatility: float,
        momentum: float,
        breakout_strength: float,
        btc_aligned: bool = True,
        timeframe_alignment: bool = True,
        market_is_sideways: bool = False,
    ) -> None:
        evaluate_entry(
            {
                "symbol": symbol,
                "close": close,
                "rsi": rsi,
                "macd_histogram": macd_histogram,
                "ma_fast": ma_fast,
                "ma_slow": ma_slow,
                "trend_strength": trend_strength,
                "relative_volume": relative_volume,
                "volatility": volatility,
                "momentum": momentum,
                "breakout_strength": breakout_strength,
                "btc_aligned": btc_aligned,
                "timeframe_alignment": timeframe_alignment,
                "market_is_sideways": market_is_sideways,
            }
        )


def run() -> None:
    if not app:
        render_dashboard()
        return
    app()


if __name__ == "__main__":
    run()
