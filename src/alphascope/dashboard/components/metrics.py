from __future__ import annotations

from alphascope.dashboard._optional import st


def metric_card(label: str, value, delta=None) -> None:
    st.metric(label=label, value=value, delta=delta)


def system_status_card(title: str, payload: dict) -> None:
    with st.container(border=True):
        st.subheader(title)
        if not payload:
            st.caption("No data available")
            return
        for key, value in payload.items():
            st.write(f"**{key}**: {value}")
