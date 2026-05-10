from __future__ import annotations

from alphascope.dashboard._optional import st

from alphascope.dashboard.components.metrics import system_status_card
from alphascope.dashboard.services.data_service import DashboardDataService
from alphascope.monitoring.system_status import SystemStatusService


def render() -> None:
    st.title("System Monitor")
    status = SystemStatusService().get_status()
    data_service = DashboardDataService()

    col1, col2, col3 = st.columns(3)
    with col1:
        system_status_card("System Metrics", status.get("system_metrics", {}))
    with col2:
        system_status_card("Scheduler", status.get("scheduler", {}))
    with col3:
        system_status_card("Pipeline", status.get("pipeline", {}))

    st.subheader("System Log")
    system_log = "\n".join(data_service.load_recent_logs("system.log", lines=100))
    st.code(system_log or "No system log available", language="log")

    st.subheader("Trading Log")
    trading_log = "\n".join(data_service.load_recent_logs("trading.log", lines=100))
    st.code(trading_log or "No trading log available", language="log")
