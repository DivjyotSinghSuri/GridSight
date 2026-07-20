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
import streamlit as st

from .config import PAGE_TITLE, PAGE_ICON
from .components.sidebar import render_sidebar
from .dashboard.overview import render_overview
from .dashboard.forecast import render_forecasts

st.set_page_config(
    page_title=PAGE_TITLE,
    page_icon=PAGE_ICON,
    layout="wide",
)

st.markdown(
    """
    <style>
        .block-container {padding-top: 2rem; padding-bottom: 3rem;}
        [data-testid="stMetricValue"] {font-size: 1.6rem;}
        [data-testid="stMetricLabel"] {font-size: 0.85rem; color: #6B7280;}
    </style>
    """,
    unsafe_allow_html=True,
)

page = render_sidebar()

if page == "Overview":
    render_overview()
if page == "Forecast":
    render_forecasts()
