from __future__ import annotations

class _StreamlitShim:
    def __getattr__(self, name):
        raise RuntimeError("streamlit is not installed. Install requirements-full.txt to use the dashboard.")

st = _StreamlitShim()

try:
    import streamlit as real_streamlit
    st = real_streamlit
except Exception:
    pass
