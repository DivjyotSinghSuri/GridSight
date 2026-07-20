"""
Pipeline Health page.

Operational monitoring dashboard for the GridSight ELT + forecasting
pipeline: layer health, freshness, warehouse volumes and data quality
checks — every status shown here is computed live from the warehouse,
never hardcoded.
"""

import pandas as pd
import streamlit as st
import plotly.express as px

from utils.queries import (
    load_latest_run_metadata,
    load_warehouse_statistics,
    load_latest_dataset_updates,
    load_pipeline_status,
)

st.set_page_config(
    page_title="Pipeline Health",
    page_icon="⚙️",
    layout="wide",
)

st.title("⚙️ Pipeline Health")
st.caption("Monitor the health of the GridSight ELT pipeline.")

# ----------------------------------------------------
# Load Data
# ----------------------------------------------------

@st.cache_data
def load_data():
    return (
        load_latest_run_metadata(),
        load_warehouse_statistics(),
        load_latest_dataset_updates(),
        load_pipeline_status(),
    )


metadata_df, stats_df, updates_df, status_df = load_data()

if metadata_df.empty:
    st.error("No pipeline information available.")
    st.stop()

metadata = metadata_df.iloc[0]
stats = stats_df.iloc[0]
updates = updates_df.iloc[0]
status = status_df.iloc[0]

# Layer-level health, computed once from live status so every badge,
# table and summary sentence on this page stays consistent.
layer_status = {
    "Bronze": status["weather_status"],
    "Silver": status["feature_status"],
    "Gold": "Healthy" if metadata["forecast_rows"] > 0 else "Missing",
    "Forecast": status["forecast_status"],
}


def layer_badge(value: str) -> str:
    """Renders a Healthy/Missing status as a colored KPI badge."""
    return "🟢 Healthy" if value == "Healthy" else "🔴 Failed"


def quality_badge(value: str) -> str:
    """Renders a Healthy/Missing status as a pass/fail check mark."""
    return "✅ Passed" if value == "Healthy" else "❌ Failed"


st.header("Overall Pipeline Status")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Bronze", layer_badge(layer_status["Bronze"]))
col2.metric("Silver", layer_badge(layer_status["Silver"]))
col3.metric("Gold", layer_badge(layer_status["Gold"]))
col4.metric("Forecast", layer_badge(layer_status["Forecast"]))

st.divider()

st.header("Latest Forecast Run")

c1, c2, c3 = st.columns(3)

c1.metric("Model", metadata["model_name"])
c2.metric("Version", metadata["model_version"])
c3.metric("Forecast Rows", int(metadata["forecast_rows"]))

c1, c2, c3 = st.columns(3)

c1.metric("Forecast Start", str(metadata["forecast_start"]))
c2.metric("Forecast End", str(metadata["forecast_end"]))
c3.metric("Created At", str(metadata["forecast_created_at"]))

st.divider()

st.header("Pipeline Architecture")

st.markdown(
    """
```text
Open-Meteo APIs
        │
        ▼
🟤 Bronze Layer (Amazon S3)
        │
        ▼
🔵 Silver Layer (DuckDB + dbt)
        │
        ▼
🟡 Gold Layer
Training Dataset
Forecast Features
        │
        ▼
🟢 Ridge Regression
        │
        ▼
🔴 Forecast Output
gold_forecasts
```
"""
)

# ----------------------------------------------------
# Data Freshness
# ----------------------------------------------------

st.divider()
st.header("Data Freshness")

freshness = pd.DataFrame(
    {
        "Dataset": ["Weather", "Generation", "Irradiance", "Daylight", "Forecast"],
        "Latest Record": [
            updates["latest_weather"],
            updates["latest_generation"],
            updates["latest_irradiance"],
            updates["latest_daylight"],
            updates["latest_forecast"],
        ],
    }
)

st.dataframe(freshness, use_container_width=True)

# ----------------------------------------------------
# Warehouse Statistics
# ----------------------------------------------------

st.divider()
st.header("Warehouse Statistics")

warehouse_df = pd.DataFrame(
    {
        "Table": [
            "Weather",
            "Generation",
            "Irradiance",
            "Daylight",
            "Training Dataset",
            "Forecast Features",
            "Forecasts",
        ],
        "Rows": [
            stats["weather_rows"],
            stats["generation_rows"],
            stats["irradiance_rows"],
            stats["daylight_rows"],
            stats["training_rows"],
            stats["forecast_feature_rows"],
            stats["forecast_rows"],
        ],
    }
)

fig = px.bar(
    warehouse_df,
    x="Rows",
    y="Table",
    orientation="h",
    text="Rows",
)

fig.update_layout(
    template="plotly_white",
    height=500,
    yaxis_title="",
    xaxis_title="Rows",
    margin=dict(l=20, r=20, t=20, b=20),
)

st.plotly_chart(fig, use_container_width=True)

st.divider()

st.header("Pipeline Metrics")

c1, c2, c3, c4 = st.columns(4)

c1.metric("Weather Rows", f"{stats['weather_rows']:,}")
c2.metric("Generation Rows", f"{stats['generation_rows']:,}")
c3.metric("Forecast Features", f"{stats['forecast_feature_rows']:,}")
c4.metric("Forecast Rows", f"{stats['forecast_rows']:,}")

st.divider()

st.header("Dataset Distribution")

fig = px.pie(warehouse_df, names="Table", values="Rows")
fig.update_layout(template="plotly_white", height=550)
st.plotly_chart(fig, use_container_width=True)

# ----------------------------------------------------
# Data Quality
# ----------------------------------------------------

st.divider()
st.header("Data Quality Checks")

quality = pd.DataFrame(
    {
        "Check": [
            "Weather Available",
            "Generation Available",
            "Irradiance Available",
            "Daylight Available",
            "Forecast Features",
            "Forecast Output",
        ],
        "Status": [
            status["weather_status"],
            status["generation_status"],
            status["irradiance_status"],
            status["daylight_status"],
            status["feature_status"],
            status["forecast_status"],
        ],
    }
)

quality["Result"] = quality["Status"].apply(quality_badge)

st.dataframe(quality, use_container_width=True, hide_index=True)

st.divider()

st.header("Storage Overview")

storage = pd.DataFrame(
    {
        "Layer": ["Bronze", "Silver", "Gold", "Forecast"],
        "Description": [
            "Raw API Data (Amazon S3)",
            "dbt Staging Models",
            "Training Dataset & Forecast Features",
            "Forecast Output",
        ],
        "Status": [
            layer_status["Bronze"],
            layer_status["Silver"],
            layer_status["Gold"],
            layer_status["Forecast"],
        ],
    }
)

st.dataframe(storage, use_container_width=True, hide_index=True)

st.divider()

st.header("Forecast Coverage")

coverage = pd.DataFrame(
    {
        "Metric": [
            "Forecast Start",
            "Forecast End",
            "Forecast Horizon (Rows)",
        ],
        "Value": [
            metadata["forecast_start"],
            metadata["forecast_end"],
            metadata["forecast_rows"],
        ],
    }
)

st.table(coverage)

# ----------------------------------------------------
# Pipeline Timeline
# ----------------------------------------------------

st.divider()
st.header("Pipeline Timeline")

timeline = pd.DataFrame(
    {
        "Stage": [
            "Weather Ingestion",
            "Generation Ingestion",
            "Irradiance Ingestion",
            "dbt Transformations",
            "Feature Engineering",
            "Forecast Generation",
        ],
        "Latest Execution": [
            updates["latest_weather"],
            updates["latest_generation"],
            updates["latest_irradiance"],
            metadata["forecast_created_at"],
            metadata["forecast_created_at"],
            metadata["forecast_created_at"],
        ],
        "Status": [
            quality_badge(status["weather_status"]),
            quality_badge(status["generation_status"]),
            quality_badge(status["irradiance_status"]),
            quality_badge(status["feature_status"]),
            quality_badge(status["feature_status"]),
            quality_badge(status["forecast_status"]),
        ],
    }
)

st.dataframe(timeline, use_container_width=True, hide_index=True)

st.divider()

st.header("Warehouse Overview")

warehouse_summary = pd.DataFrame(
    {
        "Layer": ["Bronze", "Silver", "Gold"],
        "Primary Tables": [
            "Raw Weather / Generation / Irradiance",
            "stg_weather\nstg_generation\nstg_irradiance\nstg_daylight",
            "gold_training_dataset\ngold_forecast_features\ngold_forecasts",
        ],
        "Purpose": [
            "Raw API Storage",
            "Cleaning & Standardisation",
            "Analytics & Machine Learning",
        ],
    }
)

st.dataframe(warehouse_summary, use_container_width=True, hide_index=True)

# ----------------------------------------------------
# Diagnostics
# ----------------------------------------------------

st.divider()
st.header("Diagnostics")

with st.expander("Forecast Metadata"):
    st.dataframe(metadata_df, use_container_width=True)

with st.expander("Pipeline Status"):
    st.dataframe(status_df, use_container_width=True)

with st.expander("Warehouse Statistics"):
    st.dataframe(stats_df, use_container_width=True)

with st.expander("Latest Dataset Updates"):
    st.dataframe(updates_df, use_container_width=True)

# ----------------------------------------------------
# Export
# ----------------------------------------------------

st.divider()
st.header("Export")

col1, col2 = st.columns(2)

with col1:

    st.download_button(
        label="Download Warehouse Statistics",
        data=warehouse_df.to_csv(index=False),
        file_name="warehouse_statistics.csv",
        mime="text/csv",
    )

with col2:

    st.download_button(
        label="Download Pipeline Timeline",
        data=timeline.to_csv(index=False),
        file_name="pipeline_timeline.csv",
        mime="text/csv",
    )

st.divider()


def summary_icon(value: str) -> str:
    """Check/cross icon for the closing pipeline summary, driven by live status."""
    return "✅" if value == "Healthy" else "❌"


st.success(
    f"""
### GridSight Pipeline Summary

- {summary_icon(layer_status['Bronze'])} Bronze Layer Operational
- {summary_icon(layer_status['Silver'])} Silver Transformations Successful
- {summary_icon(layer_status['Gold'])} Gold Dataset Available
- {summary_icon(layer_status['Forecast'])} Ridge Regression Forecast Generated
- ✅ {int(metadata["forecast_rows"])} Forecast Records Available
- ✅ Model Version: {metadata["model_version"]}
"""
)

st.divider()

st.caption(
    "GridSight • Cloud-Native Renewable Energy Forecasting Platform | "
    "Amazon S3 • DuckDB • dbt • Ridge Regression • Streamlit"
)