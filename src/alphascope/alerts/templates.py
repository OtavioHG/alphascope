"""Telegram alert message templates for AlphaScope runtime events."""

from __future__ import annotations

from typing import Any


def render_test_alert(*, app_name: str, environment: str, source: str) -> str:
    return "\n".join(
        [
            "AlphaScope test alert",
            f"env: {environment}",
            f"source: {source}",
            f"app: {app_name}",
        ]
    )


def render_pipeline_completed(payload: dict[str, Any]) -> str:
    return "\n".join(
        [
            "Pipeline completed",
            f"cycle: {payload.get('cycle_number', '-')}",
            f"ranking rows: {payload.get('ranking_rows', 0)}",
            f"trades: {payload.get('trades_executed', 0)}",
            f"news rows: {payload.get('news_rows', 0)}",
            f"duration: {payload.get('duration_seconds', 0.0):.2f}s",
        ]
    )


def render_critical_error(payload: dict[str, Any]) -> str:
    return "\n".join(
        [
            "Critical error",
            f"component: {payload.get('component', '-')}",
            f"message: {payload.get('error', '-')}",
        ]
    )


def render_top_ranking(payload: dict[str, Any]) -> str:
    return "\n".join(
        [
            "New top ranking",
            f"symbol: {payload.get('symbol', '-')}",
            f"score: {float(payload.get('score', 0.0)):.4f}",
            f"rank: {payload.get('rank', 1)}",
        ]
    )


def render_trade_opened(payload: dict[str, Any]) -> str:
    mode = str(payload.get("mode", "paper")).upper()
    return "\n".join(
        [
            f"Trade opened [{mode}]",
            f"symbol: {payload.get('symbol', '-')}",
            f"side: {payload.get('side', 'BUY')}",
            f"qty: {float(payload.get('quantity', 0.0)):.6f}",
            f"price: {float(payload.get('price', 0.0)):.6f}",
            f"score: {float(payload.get('score', 0.0) or 0.0):.4f}",
        ]
    )


def render_trade_closed(payload: dict[str, Any]) -> str:
    mode = str(payload.get("mode", "paper")).upper()
    return "\n".join(
        [
            f"Trade closed [{mode}]",
            f"symbol: {payload.get('symbol', '-')}",
            f"side: {payload.get('side', 'SELL')}",
            f"qty: {float(payload.get('quantity', 0.0)):.6f}",
            f"price: {float(payload.get('price', 0.0)):.6f}",
            f"realized pnl: {float(payload.get('realized_pnl', 0.0)):.4f}",
            f"reason: {payload.get('reason', '-')}",
        ]
    )


def render_portfolio_snapshot(payload: dict[str, Any]) -> str:
    return "\n".join(
        [
            str(payload.get("label", "Portfolio snapshot")),
            f"equity: {float(payload.get('equity', 0.0)):.4f}",
            f"cash: {float(payload.get('cash', 0.0)):.4f}",
            f"open positions: {int(payload.get('open_positions', 0))}",
            f"realized pnl: {float(payload.get('realized_pnl', 0.0)):.4f}",
            f"unrealized pnl: {float(payload.get('unrealized_pnl', 0.0)):.4f}",
        ]
    )


def render_heartbeat_lost(payload: dict[str, Any]) -> str:
    return "\n".join(
        [
            "Heartbeat alert",
            f"issue: {payload.get('issue_code', 'stale_heartbeat')}",
            f"heartbeat at: {payload.get('heartbeat_timestamp', '-')}",
            f"daemon status: {payload.get('daemon_status', '-')}",
        ]
    )


def render_daemon_stopped(payload: dict[str, Any]) -> str:
    return "\n".join(
        [
            "Daemon stopped",
            f"status: {payload.get('status', 'stopped')}",
            f"cycles: {payload.get('cycle_count', 0)}",
            f"errors: {payload.get('consecutive_errors', 0)}",
        ]
    )


def render_runtime_summary(payload: dict[str, Any]) -> str:
    return "\n".join(
        [
            str(payload.get("label", "Runtime summary")),
            f"daemon: {payload.get('daemon_status', '-')}",
            f"heartbeat: {payload.get('heartbeat_status', '-')}",
            f"top: {payload.get('top_symbol', '-')}",
            f"equity: {float(payload.get('equity', 0.0)):.4f}",
            f"cash: {float(payload.get('cash', 0.0)):.4f}",
            f"jobs: {int(payload.get('job_count', 0))}",
            f"issues: {int(payload.get('issue_count', 0))}",
        ]
    )


def render_multi_agent_decision(payload: dict[str, Any]) -> str:
    return "\n".join(
        [
            "Multi-Agent Decision",
            f"symbol: {payload.get('symbol', '-')}",
            f"timeframe: {payload.get('timeframe', '-')}",
            f"decision: {payload.get('decision', '-')}",
            f"score: {float(payload.get('final_score', 0.0)):.4f}",
            f"consensus: {payload.get('consensus', '-')}",
            f"execution: {payload.get('execution_action', '-')}",
            f"reason: {payload.get('reasoning', '-')}",
        ]
    )
