"""Terminal UI helpers for AlphaScope CLI."""

from __future__ import annotations

import json
from typing import Any

try:  # pragma: no cover - optional import for lightweight CLI bootstrap
    import pandas as pd
except Exception:  # pragma: no cover - allows --help/build_parser without pandas installed
    pd = None  # type: ignore[assignment]
from rich.box import ROUNDED
from rich.console import Console
from rich.json import JSON
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()

_PALETTE = {
    "primary": "bold cyan",
    "secondary": "bright_black",
    "success": "bold green",
    "warning": "bold yellow",
    "error": "bold red",
    "accent": "bold magenta",
    "info": "bright_white",
}


def print_header(subtitle: str | None = None) -> None:
    """Render the main AlphaScope header."""
    title = Text("AlphaScope", style="bold white on dark_blue")
    title.append("  V1", style="bold cyan")
    body = "[bold]Quantitative Crypto Terminal[/bold]"
    if subtitle:
        body = f"{body}\n[{_PALETTE['secondary']}]{subtitle}[/{_PALETTE['secondary']}]"
    console.print(Panel.fit(body, title=title, border_style="cyan", box=ROUNDED, padding=(1, 2)))


def print_section(title: str) -> None:
    """Render a small section divider."""
    console.print(f"\n[{_PALETTE['primary']}]{title}[/{_PALETTE['primary']}]")


def print_success(message: str) -> None:
    """Render a success message."""
    console.print(f"[{_PALETTE['success']}]OK[/{_PALETTE['success']}] {message}")


def print_warning(message: str) -> None:
    """Render a warning message."""
    console.print(f"[{_PALETTE['warning']}]WARN[/{_PALETTE['warning']}] {message}")


def print_error(message: str) -> None:
    """Render an error message."""
    console.print(f"[{_PALETTE['error']}]ERROR[/{_PALETTE['error']}] {message}")


def print_json(payload: dict[str, Any] | list[dict[str, Any]]) -> None:
    """Render JSON with syntax highlighting."""
    console.print(JSON.from_data(payload))


def print_table_from_dataframe(
    dataframe: pd.DataFrame,
    *,
    title: str,
    max_rows: int | None = None,
    index: bool = False,
) -> None:
    """Render a pandas DataFrame as a Rich table."""
    if dataframe.empty:
        print_warning(f"{title}: nenhum dado encontrado.")
        return

    frame = dataframe.copy()
    if max_rows is not None:
        frame = frame.head(max_rows)
    frame = _format_dataframe(frame)

    table = Table(title=title, box=ROUNDED, border_style="cyan", header_style="bold white on dark_blue")
    if index:
        table.add_column("#", justify="right", style="bright_black")
    for column in frame.columns:
        justify = "right" if _is_numeric_column(frame[column]) else "left"
        table.add_column(str(column), justify=justify, overflow="fold")

    for idx, row in enumerate(frame.itertuples(index=False), start=1):
        values = [str(value) for value in row]
        if index:
            table.add_row(str(idx), *values)
        else:
            table.add_row(*values)

    console.print(table)


def print_kv_panel(title: str, values: dict[str, Any], *, border_style: str = "cyan") -> None:
    """Render key-value metrics inside a panel."""
    body = "\n".join(f"[bold]{key}:[/bold] {_format_value(value)}" for key, value in values.items())
    console.print(Panel(body, title=title, border_style=border_style, box=ROUNDED, padding=(1, 2)))


def print_backtest_result(metrics: dict[str, Any], trades: pd.DataFrame, equity_curve: pd.DataFrame) -> None:
    """Render backtest metrics, trades and equity curve."""
    print_section("Backtest Metrics")
    print_kv_panel("Performance", metrics, border_style="magenta")

    print_section("Trades")
    print_table_from_dataframe(trades, title="Executed Trades")

    print_section("Equity Curve")
    columns = [column for column in ["timestamp", "signal", "equity", "cash", "quantity", "close"] if column in equity_curve.columns]
    print_table_from_dataframe(equity_curve.loc[:, columns], title="Equity Curve", max_rows=20)


def print_pipeline_summary(summary: dict[str, Any]) -> None:
    """Render a compact pipeline summary."""
    ingestion_rows = sum(int(item.get("rows", 0)) for item in summary.get("ingestion", []))
    values = {
        "Ingestion rows": ingestion_rows,
        "Feature rows": summary.get("feature_rows", 0),
        "Ranking rows": summary.get("ranking_rows", 0),
        "Trades executed": summary.get("trades_executed", summary.get("paper_trades", 0)),
        "Trader": summary.get("selected_trader", "PaperTrader"),
    }
    print_kv_panel("Pipeline Summary", values, border_style="green")


def print_snapshot(snapshot: dict[str, Any]) -> None:
    """Render the latest portfolio snapshot."""
    summary = {
        "Timestamp": snapshot.get("timestamp"),
        "Cash": snapshot.get("cash"),
        "Equity": snapshot.get("equity"),
        "Realized PnL": snapshot.get("realized_pnl"),
        "Unrealized PnL": snapshot.get("unrealized_pnl"),
    }
    print_kv_panel("Portfolio Snapshot", summary, border_style="green")

    positions = snapshot.get("positions_json", {})
    if positions:
        frame = pd.DataFrame(positions.values())
        print_table_from_dataframe(frame, title="Open Positions")
    else:
        print_warning("Snapshot sem posicoes abertas.")


def print_jobs_status(jobs: list[dict[str, Any]]) -> None:
    """Render scheduler jobs and runtime counters."""
    if not jobs:
        print_warning("Nenhum job registrado.")
        return
    frame = pd.DataFrame(jobs)
    preferred = [
        "name",
        "enabled",
        "interval_seconds",
        "total_runs",
        "successful_runs",
        "failed_runs",
        "consecutive_failures",
        "next_run_at",
        "last_error",
    ]
    visible = [column for column in preferred if column in frame.columns]
    print_table_from_dataframe(frame.loc[:, visible], title="Scheduler Jobs", max_rows=50)


def print_runtime_status(status: dict[str, Any]) -> None:
    """Render aggregated runtime status for daemon, scheduler and simulation."""
    daemon = status.get("daemon", {})
    heartbeat = status.get("heartbeat", {})
    latest_ranking = status.get("latest_ranking", {})
    latest_snapshot = status.get("latest_snapshot", {})
    jobs = status.get("jobs", {})
    cycles = status.get("cycles", {})
    database = status.get("database", {})
    apis = status.get("apis", {})
    runtime_metrics = status.get("runtime_metrics", {})
    recovery = status.get("recovery", {})

    print_kv_panel(
        "Runtime Overview",
        {
            "daemon_status": daemon.get("status", "not_running"),
            "heartbeat": heartbeat.get("status", "unavailable"),
            "heartbeat_at": heartbeat.get("timestamp"),
            "job_count": jobs.get("job_count", 0),
            "job_runs": jobs.get("total_runs", 0),
            "job_failures": jobs.get("total_failures", 0),
            "continuous_cycles": cycles.get("continuous_cycles", 0),
            "live_cycles": cycles.get("live_cycles", 0),
        },
        border_style="green",
    )
    print_kv_panel(
        "Market Runtime",
        {
            "last_ranking_at": latest_ranking.get("timestamp"),
            "ranking_rows": latest_ranking.get("rows"),
            "top_symbol": latest_ranking.get("top_symbol"),
            "top_score": latest_ranking.get("top_score"),
            "last_snapshot_at": latest_snapshot.get("timestamp"),
            "equity": latest_snapshot.get("equity"),
            "cash": latest_snapshot.get("cash"),
            "open_positions": latest_snapshot.get("open_positions"),
        },
        border_style="cyan",
    )
    print_kv_panel(
        "Infrastructure",
        {
            "sqlite_exists": database.get("exists"),
            "sqlite_path": database.get("sqlite_path"),
            **apis,
        },
        border_style="magenta",
    )
    print_kv_panel(
        "Runtime Metrics",
        {
            "metric_records": runtime_metrics.get("records", 0),
            "latest_pipeline_duration": (runtime_metrics.get("latest_values", {}) or {}).get("pipeline_duration"),
            "latest_system_errors": (runtime_metrics.get("latest_values", {}) or {}).get("system_errors"),
            "healthy": recovery.get("healthy"),
            "issues": len(recovery.get("issues", [])),
        },
        border_style="yellow",
    )


def _format_dataframe(dataframe: pd.DataFrame) -> pd.DataFrame:
    frame = dataframe.copy()
    for column in frame.columns:
        frame[column] = frame[column].map(_format_value)
    return frame


def _format_value(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:,.6f}" if abs(value) < 100 else f"{value:,.4f}"
    if pd is not None and isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat(sep=" ", timespec="seconds")
        except TypeError:
            return str(value)
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _is_numeric_column(series: Any) -> bool:
    if pd is None:
        return False
    return pd.api.types.is_numeric_dtype(series)
