"""CLI commands for the AlphaScope multi-agent system."""

from __future__ import annotations

import argparse
import json
from typing import Any

import pandas as pd

from alphascope.cli_registry import dispatch_command
from alphascope.config.settings import settings
from alphascope.ui import print_backtest_result, print_json, print_kv_panel, print_success, print_table_from_dataframe, print_warning

MULTI_AGENT_COMMANDS = {
    "run-multi-agent",
    "run-debate",
    "show-agent-output",
    "show-consensus-history",
    "run-supervisor",
    "show-agent-performance",
    "compare-agent-decisions",
    "run-live-multi-agent",
    "schedule-live-multi-agent",
    "multi-agent-runtime-status",
    "train-multi-agent-models",
    "backtest-multi-agent",
}


def add_multi_agent_subparsers(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    specs = (
        ("run-multi-agent", "Run the full multi-agent decision workflow"),
        ("run-debate", "Run only the internal multi-agent debate for one symbol"),
        ("show-agent-output", "Show persisted outputs for the selected symbol"),
        ("show-consensus-history", "Show historical supervisor consensus decisions"),
        ("run-supervisor", "Run supervisor consensus without live execution"),
        ("show-agent-performance", "Show aggregated agent activity/performance"),
        ("compare-agent-decisions", "Compare how agents disagreed or aligned"),
        ("run-live-multi-agent", "Run the live multi-agent workflow with Telegram alerts"),
        ("schedule-live-multi-agent", "Schedule continuous live multi-agent cycles"),
        ("multi-agent-runtime-status", "Show multi-agent runtime/cache/scheduler status"),
        ("train-multi-agent-models", "Train local multi-agent models with available ML libraries"),
        ("backtest-multi-agent", "Run historical multi-agent backtest"),
    )
    for command_name, help_text in specs:
        parser = subparsers.add_parser(command_name, help=help_text)
        if command_name in {"run-multi-agent", "run-debate", "run-supervisor", "run-live-multi-agent", "show-agent-output", "compare-agent-decisions", "backtest-multi-agent"}:
            parser.add_argument("--symbol", default=settings.symbol_list[0])
            parser.add_argument("--interval", default=settings.default_interval)
        if command_name in {"show-consensus-history", "show-agent-performance", "train-multi-agent-models"}:
            parser.add_argument("--limit", type=int, default=20)
        if command_name == "show-consensus-history":
            parser.add_argument("--symbol", default=None)
        if command_name == "show-agent-output":
            parser.add_argument("--limit", type=int, default=20)
        if command_name == "compare-agent-decisions":
            parser.add_argument("--limit", type=int, default=20)
        if command_name == "schedule-live-multi-agent":
            parser.add_argument("--symbols", default=",".join(settings.symbol_list))
            parser.add_argument("--interval", default=settings.default_interval)
            parser.add_argument("--cycle-seconds", type=int, default=settings.cycle_interval_seconds)
            parser.add_argument("--duration-seconds", type=int, default=60)
        if command_name == "backtest-multi-agent":
            parser.add_argument("--limit", type=int, default=300)
        if command_name == "train-multi-agent-models":
            parser.add_argument("--symbols", default=",".join(settings.symbol_list))
            parser.add_argument("--interval", default=settings.default_interval)
            parser.add_argument("--cycle-count", type=int, default=1)
        if command_name == "multi-agent-runtime-status":
            parser.add_argument("--json", action="store_true", dest="as_json")


def handle_multi_agent_command(args: argparse.Namespace, **_: Any) -> bool:
    return dispatch_command(args.command, MULTI_AGENT_HANDLERS, args=args)


def _handle_run_multi_agent(args: argparse.Namespace, **_: Any) -> None:
    from alphascope.agents.orchestrator import MultiAgentOrchestrator

    orchestrator = MultiAgentOrchestrator()
    try:
        result = orchestrator.run(symbol=args.symbol.upper(), timeframe=args.interval, mode="paper", send_telegram=True, execute_plan=True)
    finally:
        orchestrator.close()
    print_success("Ciclo multiagente executado.")
    print_kv_panel("Supervisor", result.supervisor.to_dict())
    print_kv_panel("Execution", result.execution.to_dict())
    if result.runtime_event.get("execution_result"):
        print_kv_panel("Execution Result", result.runtime_event["execution_result"])


def _handle_run_debate(args: argparse.Namespace, **_: Any) -> None:
    from alphascope.agents.orchestrator import MultiAgentOrchestrator

    orchestrator = MultiAgentOrchestrator()
    try:
        result = orchestrator.run(symbol=args.symbol.upper(), timeframe=args.interval, mode="analysis", send_telegram=False, execute_plan=False)
    finally:
        orchestrator.close()
    frame = pd.DataFrame([item.to_dict() for item in result.debate])
    if frame.empty:
        print_warning("Nenhum debate gerado.")
        return
    print_success("Debate multiagente gerado.")
    print_table_from_dataframe(frame, title="Agent Debate", max_rows=20)


def _handle_show_agent_output(args: argparse.Namespace, **_: Any) -> None:
    from alphascope.agents.repository import MultiAgentRepository

    rows = MultiAgentRepository().get_recent_agent_decisions(symbol=args.symbol.upper(), limit=args.limit)
    frame = pd.DataFrame(rows)
    if frame.empty:
        print_warning("Nenhum output de agente encontrado.")
        return
    columns = [column for column in ["created_at", "agent", "signal", "confidence", "score", "model_name", "reasoning"] if column in frame.columns]
    print_table_from_dataframe(frame.loc[:, columns], title=f"Agent Outputs | {args.symbol.upper()}", max_rows=args.limit)


def _handle_show_consensus_history(args: argparse.Namespace, **_: Any) -> None:
    from alphascope.agents.repository import MultiAgentRepository

    rows = MultiAgentRepository().get_recent_consensus(symbol=args.symbol.upper() if args.symbol else None, limit=args.limit)
    frame = pd.DataFrame(rows)
    if frame.empty:
        print_warning("Nenhum consenso salvo encontrado.")
        return
    columns = [column for column in ["created_at", "symbol", "decision", "final_score", "consensus", "reasoning"] if column in frame.columns]
    print_table_from_dataframe(frame.loc[:, columns], title="Consensus History", max_rows=args.limit)


def _handle_run_supervisor(args: argparse.Namespace, **_: Any) -> None:
    from alphascope.agents.orchestrator import MultiAgentOrchestrator

    orchestrator = MultiAgentOrchestrator()
    try:
        result = orchestrator.run(symbol=args.symbol.upper(), timeframe=args.interval, mode="supervisor", send_telegram=False, execute_plan=False)
    finally:
        orchestrator.close()
    print_success("Supervisor executado.")
    print(json.dumps(result.supervisor.to_dict(), indent=2, ensure_ascii=False))


def _handle_show_agent_performance(args: argparse.Namespace, **_: Any) -> None:
    from alphascope.agents.repository import MultiAgentRepository

    rows = MultiAgentRepository().get_agent_performance(limit=args.limit * 10)
    frame = pd.DataFrame(rows)
    if frame.empty:
        print_warning("Ainda nao ha performance consolidada dos agentes.")
        return
    print_table_from_dataframe(frame, title="Agent Performance", max_rows=args.limit)


def _handle_compare_agent_decisions(args: argparse.Namespace, **_: Any) -> None:
    from alphascope.agents.repository import MultiAgentRepository

    rows = MultiAgentRepository().compare_agent_decisions(symbol=args.symbol.upper(), limit=args.limit)
    if not rows:
        print_warning("Nenhuma comparacao disponivel.")
        return
    frame = pd.DataFrame(
        [{"symbol": row["symbol"], "created_at": row["created_at"], "signals": json.dumps(row["signals"], ensure_ascii=False)} for row in rows]
    )
    print_table_from_dataframe(frame, title="Agent Decision Comparison", max_rows=args.limit)


def _handle_run_live_multi_agent(args: argparse.Namespace, **_: Any) -> None:
    from alphascope.agents.runtime import MultiAgentRuntime

    runtime = MultiAgentRuntime()
    try:
        payload = runtime.run_cycle(symbol=args.symbol.upper(), timeframe=args.interval, mode="live", send_telegram=True)
    finally:
        runtime.close()
    supervisor = payload.get("supervisor", {}) if isinstance(payload.get("supervisor"), dict) else {}
    execution = payload.get("execution", {}) if isinstance(payload.get("execution"), dict) else {}
    runtime_event = payload.get("runtime_event", {}) if isinstance(payload.get("runtime_event"), dict) else {}
    print_success("Fluxo live multiagente executado.")
    print_kv_panel(
        "Live Multi-Agent",
        {
            "decision": supervisor.get("decision"),
            "final_score": supervisor.get("final_score"),
            "action": execution.get("action"),
            "execution_result": runtime_event.get("execution_result"),
        },
    )


def _handle_schedule_live_multi_agent(args: argparse.Namespace, **_: Any) -> None:
    from alphascope.agents.runtime import MultiAgentRuntime

    runtime = MultiAgentRuntime()
    symbols = [symbol.strip().upper() for symbol in str(args.symbols).split(",") if symbol.strip()]
    try:
        jobs = runtime.schedule_live(symbols=symbols, timeframe=args.interval, cycle_seconds=args.cycle_seconds, duration_seconds=args.duration_seconds)
    finally:
        runtime.close()
    frame = pd.DataFrame(jobs)
    print_success("Scheduler multiagente executado.")
    if not frame.empty:
        print_table_from_dataframe(frame, title="Multi-Agent Scheduler Jobs", max_rows=20)


def _handle_multi_agent_runtime_status(args: argparse.Namespace, **_: Any) -> None:
    from alphascope.agents.runtime import MultiAgentRuntime

    runtime = MultiAgentRuntime()
    try:
        payload = runtime.status()
    finally:
        runtime.close()
    if getattr(args, "as_json", False):
        print(json.dumps(payload, indent=2, ensure_ascii=False, default=str))
        return
    print_kv_panel("Multi-Agent Runtime", payload)


def _handle_train_multi_agent_models(args: argparse.Namespace, **_: Any) -> None:
    from alphascope.agents.runtime import MultiAgentRuntime

    runtime = MultiAgentRuntime()
    symbols = [symbol.strip().upper() for symbol in str(args.symbols).split(",") if symbol.strip()]
    try:
        result = runtime.train_models(symbols=symbols, timeframe=args.interval, cycle_count=args.cycle_count)
    finally:
        runtime.close()
    print_success("Treino multiagente executado.")
    print_json(result)


def _handle_backtest_multi_agent(args: argparse.Namespace, **_: Any) -> None:
    from alphascope.agents.backtest_engine import MultiAgentBacktestEngine

    result = MultiAgentBacktestEngine().run(symbol=args.symbol.upper(), timeframe=args.interval, limit=args.limit)
    print_success(f"Backtest multiagente concluido para {args.symbol.upper()} {args.interval}.")
    print_backtest_result(metrics=result["metrics"], trades=result["trades"], equity_curve=result["equity_curve"])  # type: ignore[arg-type]
    consensus = result["consensus"]
    if isinstance(consensus, pd.DataFrame) and not consensus.empty:
        print_table_from_dataframe(consensus.tail(20).reset_index(drop=True), title="Consensus Trail", max_rows=20)


MULTI_AGENT_HANDLERS = {
    "run-multi-agent": _handle_run_multi_agent,
    "run-debate": _handle_run_debate,
    "show-agent-output": _handle_show_agent_output,
    "show-consensus-history": _handle_show_consensus_history,
    "run-supervisor": _handle_run_supervisor,
    "show-agent-performance": _handle_show_agent_performance,
    "compare-agent-decisions": _handle_compare_agent_decisions,
    "run-live-multi-agent": _handle_run_live_multi_agent,
    "schedule-live-multi-agent": _handle_schedule_live_multi_agent,
    "multi-agent-runtime-status": _handle_multi_agent_runtime_status,
    "train-multi-agent-models": _handle_train_multi_agent_models,
    "backtest-multi-agent": _handle_backtest_multi_agent,
}
