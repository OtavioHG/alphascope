from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _require_streamlit():
    try:
        import streamlit as st
    except Exception as exc:  # pragma: no cover - optional dependency at import time
        raise RuntimeError("streamlit is not installed. Install requirements-full.txt to run the dashboard.") from exc
    return st



def _run_cli_command(command: str) -> tuple[bool, str]:
    result = subprocess.run(
        [sys.executable, "-m", "alphascope.cli", command],
        capture_output=True,
        text=True,
        timeout=120,
    )
    success = result.returncode == 0
    return success, result.stdout if success else result.stderr



def _sidebar_controls(st) -> None:
    st.sidebar.header("System Controls")
    if st.sidebar.button("Run Pipeline", use_container_width=True):
        success, output = _run_cli_command("run-pipeline")
        st.sidebar.success("Pipeline executed" if success else "Pipeline failed")
        st.sidebar.code(output or "No output")
    if st.sidebar.button("Refresh Ranking", use_container_width=True):
        success, output = _run_cli_command("run-pipeline")
        st.sidebar.success("Ranking refreshed" if success else "Refresh failed")
        st.sidebar.code(output or "No output")

    scheduler_state_path = Path("data/processed/system/scheduler_state.json")
    if st.sidebar.button("Pause Scheduler", use_container_width=True):
        scheduler_state_path.parent.mkdir(parents=True, exist_ok=True)
        scheduler_state_path.write_text('{"status":"paused"}', encoding="utf-8")
        st.sidebar.info("Scheduler marked as paused")
    if st.sidebar.button("Resume Scheduler", use_container_width=True):
        scheduler_state_path.parent.mkdir(parents=True, exist_ok=True)
        scheduler_state_path.write_text('{"status":"running"}', encoding="utf-8")
        st.sidebar.info("Scheduler marked as running")



def _pages():
    from alphascope.dashboard.pages import (
        asset_ranking,
        market_analysis,
        multi_agent_monitor,
        news_sentiment,
        overview,
        system_monitor,
        trading_monitor,
    )

    return {
        "Overview": overview.render,
        "Market Analysis": market_analysis.render,
        "Asset Ranking": asset_ranking.render,
        "News Sentiment": news_sentiment.render,
        "Trading Monitor": trading_monitor.render,
        "System Monitor": system_monitor.render,
        "Multi-Agent Monitor": multi_agent_monitor.render,
    }



def main() -> None:
    st = _require_streamlit()
    st.set_page_config(page_title="AlphaScope Dashboard", layout="wide")
    _sidebar_controls(st)
    pages = _pages()
    selection = st.sidebar.radio("Navigate", list(pages.keys()))
    pages[selection]()


if __name__ == "__main__":
    main()
