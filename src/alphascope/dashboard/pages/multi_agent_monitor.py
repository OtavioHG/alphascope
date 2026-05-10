from __future__ import annotations

import pandas as pd
from alphascope.dashboard._optional import st

from alphascope.agents.runtime import MultiAgentRuntime
from alphascope.dashboard.components.metrics import metric_card
from alphascope.dashboard.services.trading_service import TradingService
from alphascope.monitoring.metrics import MetricsCollector


def render() -> None:
    st.title("Multi-Agent Monitor")
    runtime = MultiAgentRuntime()
    trading = TradingService()
    try:
        status = runtime.status()
    finally:
        runtime.close()

    cache = status.get("cache", {}) if isinstance(status.get("cache"), dict) else {}
    heartbeat = status.get("heartbeat", {}) if isinstance(status.get("heartbeat"), dict) else {}
    scheduler = status.get("scheduler", {}) if isinstance(status.get("scheduler"), dict) else {}

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        metric_card("Last Decision", status.get("last_decision", "-"))
    with col2:
        metric_card("Last Score", round(float(status.get("last_score", 0.0) or 0.0), 4))
    with col3:
        metric_card("Cache Backend", cache.get("backend", "-"))
    with col4:
        metric_card("Scheduler Jobs", scheduler.get("job_count", len(scheduler.get("jobs", [])) if isinstance(scheduler.get("jobs"), list) else 0))

    st.subheader("Runtime Status")
    st.json(status)

    consensus = trading.repository.get_audit_events(limit=50)
    if not consensus.empty and "action" in consensus.columns:
        consensus = consensus.loc[consensus["action"].astype(str) == "multi_agent_decision"].reset_index(drop=True)
    st.subheader("Recent Multi-Agent Audit Events")
    if consensus.empty:
        st.info("No multi-agent audit events available")
    else:
        st.dataframe(consensus.head(20), use_container_width=True)

    st.subheader("Recent Multi-Agent Prometheus Metrics")
    rendered = MetricsCollector().render_prometheus()
    filtered = [line for line in rendered.splitlines() if line.startswith("multi_agent_")]
    st.code("\n".join(filtered) or "No multi-agent metrics emitted yet", language="text")

    st.subheader("Heartbeat")
    st.json(heartbeat if heartbeat else {"status": "missing"})
