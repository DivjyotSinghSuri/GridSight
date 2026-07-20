"""Custom sidebar: logo, navigation, and status footer."""
import streamlit as st

from config import PAGE_ICON, NAV_PAGES
from components.utils import load_metrics, last_pipeline_run_utc, database_is_reachable


def render_sidebar() -> str:
    with st.sidebar:
        st.markdown(f"## {PAGE_ICON} GridSight")
        st.caption("Renewable Energy Forecasting")

        page = st.radio(
            "Navigate",
            NAV_PAGES,
            label_visibility="collapsed",
        )

        st.divider()

        metrics = load_metrics()
        db_ok = database_is_reachable()

        st.caption(f"**Model version:** {metrics.get('model_version', 'v1.0')}")
        st.caption(f"**Last pipeline run:** {last_pipeline_run_utc()}")
        st.caption(f"**Database:** {'🟢 Connected' if db_ok else '🔴 Unavailable'}")

    return page