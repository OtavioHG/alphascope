"""Platform control commands bridging legacy argparse CLI and the new control plane."""

from __future__ import annotations

import argparse
from typing import Any

from alphascope.cli_registry import dispatch_command


PLATFORM_COMMANDS = {
    "control-center",
    "platform-status",
    "run-platform-api",
    "run-telegram-bot",
    "run-dashboard",
}


def add_platform_subparsers(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    subparsers.add_parser("control-center", help="Open the professional control center dashboard")
    subparsers.add_parser("platform-status", help="Show platform status, risk and portfolio snapshot")

    api_parser = subparsers.add_parser("run-platform-api", help="Run the FastAPI platform backend")
    api_parser.add_argument("--host", default="0.0.0.0")
    api_parser.add_argument("--port", type=int, default=8010)

    bot_parser = subparsers.add_parser("run-telegram-bot", help="Run the Telegram control bot")
    bot_parser.add_argument("--once", action="store_true")

    dashboard_parser = subparsers.add_parser("run-dashboard", help="Run the official Streamlit dashboard")
    dashboard_parser.add_argument("--host", default="0.0.0.0")
    dashboard_parser.add_argument("--port", type=int, default=8501)


def handle_platform_command(args: argparse.Namespace, **_: Any) -> bool:
    return dispatch_command(args.command, PLATFORM_HANDLERS, args=args)


def _handle_control_center(args: argparse.Namespace, **_: Any) -> None:
    from alphascope.control_center_cli import render_dashboard

    _ = args
    render_dashboard()


def _handle_platform_status(args: argparse.Namespace, **_: Any) -> None:
    from alphascope.control_center_cli import render_status

    _ = args
    render_status()


def _handle_run_platform_api(args: argparse.Namespace, **_: Any) -> None:
    try:
        import uvicorn
    except Exception as exc:  # pragma: no cover - optional dependency
        raise RuntimeError("uvicorn is not installed. Install requirements.txt to run the platform API.") from exc

    uvicorn.run("alphascope.api.platform_api:app", host=args.host, port=args.port, reload=False)


def _handle_run_telegram_bot(args: argparse.Namespace, **_: Any) -> None:
    from alphascope.telegram_bot import PlatformTelegramBot

    bot = PlatformTelegramBot()
    if args.once:
        bot.dispatch_once()
        return
    bot.run_forever()


def _handle_run_dashboard(args: argparse.Namespace, **_: Any) -> None:
    import subprocess
    import sys

    command = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        "src/alphascope/dashboard/app.py",
        "--server.address",
        args.host,
        "--server.port",
        str(args.port),
    ]
    completed = subprocess.run(command, check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"Dashboard command failed with exit code {completed.returncode}")


PLATFORM_HANDLERS = {
    "control-center": _handle_control_center,
    "platform-status": _handle_platform_status,
    "run-platform-api": _handle_run_platform_api,
    "run-telegram-bot": _handle_run_telegram_bot,
    "run-dashboard": _handle_run_dashboard,
}
