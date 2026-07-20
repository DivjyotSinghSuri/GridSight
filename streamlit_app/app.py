"""
GridSight -- read-only Streamlit dashboard.

This app never trains models, never writes to the warehouse, and never
runs the inference pipeline. It only reads existing DuckDB tables/views
and saved model artifacts, and visualizes them (see components/utils.py
for the read-only connection policy).

Run with:
    cd streamlit_app
    streamlit run app.py
"""
import sys
from pathlib import Path

# Ensure the repository root is on sys.path so absolute package imports
# (e.g., `import streamlit_app.config`) work when running this script
# from the `streamlit_app/` directory (Streamlit runs scripts as __main__).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from streamlit_app.config import PAGE_TITLE, PAGE_ICON
from streamlit_app.components.sidebar import render_sidebar
from streamlit_app.dashboard.overview import render_overview
from streamlit_app.dashboard.forecast import render_forecasts
from streamlit_app.dashboard.weather import render_weather
from streamlit_app.dashboard.model_insights import render_model_insights
from streamlit_app.dashboard.pipeline_status import render_pipeline_status

st.set_page_config(
    page_title=PAGE_TITLE,
    page_icon=PAGE_ICON,
    layout="wide",
)

st.markdown(
    """
    <style>
        .block-container {padding-top: 2rem; padding-bottom: 3rem;}
        [data-testid="stMetricValue"] {
            font-size: 1.4rem;
            white-space: normal;
            word-break: break-word;
        }
        [data-testid="stMetricLabel"] {font-size: 0.85rem; color: #6B7280;}
    </style>
    """,
    unsafe_allow_html=True,
)

page = render_sidebar()

if page == "Overview":
    render_overview()
elif page == "Forecast":
    render_forecasts()
elif page == "Weather":
    render_weather()
elif page == "Model Insights":
    render_model_insights()
elif page == "Pipeline Status":
    render_pipeline_status()
else:
    st.info("Selected page is not implemented.")
