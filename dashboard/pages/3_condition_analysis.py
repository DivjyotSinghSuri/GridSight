"""
Condition Analysis page.

Explores the weather, irradiance and daylight conditions feeding the
current forecast — scoped to the latest 24-hour forecast window only.
"""

import streamlit as st
import plotly.express as px

from utils.queries import (
    load_conditions_for_latest_forecast,
    load_condition_summary_kpis,
)

st.set_page_config(
    page_title="Condition Analysis",
    page_icon="🌤️",
    layout="wide",
)

st.title("🌤️ Condition Analysis")
st.caption(
    "Weather, irradiance and daylight conditions behind the latest "
    "24-hour forecast."
)

# -------------------------------------------------------
# Load Data
# -------------------------------------------------------

@st.cache_data
def load_data():
    return (
        load_conditions_for_latest_forecast(),
        load_condition_summary_kpis(),
    )


conditions_df, kpi_df = load_data()

if conditions_df.empty:
    st.warning("No condition data available for the latest forecast window.")
    st.stop()

kpis = kpi_df.iloc[0]

# -------------------------------------------------------
# KPIs
# -------------------------------------------------------

col1, col2, col3, col4 = st.columns(4)

col1.metric("Avg Temperature", f"{kpis.avg_temperature:.1f} °C")
col2.metric("Avg Cloud Cover", f"{kpis.avg_cloud_cover:.1f}%")
col3.metric("Avg Radiation", f"{kpis.avg_radiation:.0f}")
col4.metric("Avg Wind Speed", f"{kpis.avg_wind_speed:.1f} km/h")

st.divider()

# -------------------------------------------------------
# Weather Trends
# -------------------------------------------------------

st.subheader("Temperature")

fig = px.line(conditions_df, x="timestamp", y="temperature_c")
fig.update_layout(
    template="plotly_white",
    height=420,
    margin=dict(l=20, r=20, t=40, b=20),
)
st.plotly_chart(fig, use_container_width=True)

st.subheader("Cloud Cover")

fig = px.area(conditions_df, x="timestamp", y="cloud_cover_pct")
fig.update_layout(template="plotly_white", height=420)
st.plotly_chart(fig, use_container_width=True)

st.subheader("Relative Humidity")

fig = px.line(conditions_df, x="timestamp", y="relative_humidity_pct")
fig.update_layout(template="plotly_white", height=420)
st.plotly_chart(fig, use_container_width=True)

st.subheader("Wind Speed")

fig = px.line(conditions_df, x="timestamp", y="wind_speed_kmh")
fig.update_layout(template="plotly_white", height=420)
st.plotly_chart(fig, use_container_width=True)

st.divider()

# -------------------------------------------------------
# Irradiance
# -------------------------------------------------------

st.header("Solar Irradiance")

fig = px.line(
    conditions_df,
    x="timestamp",
    y=[
        "shortwave_radiation",
        "direct_radiation",
        "diffuse_radiation",
    ],
)
fig.update_layout(template="plotly_white", height=500)
st.plotly_chart(fig, use_container_width=True)

fig = px.line(conditions_df, x="timestamp", y="direct_normal_irradiance")
fig.update_layout(template="plotly_white", height=420)
st.plotly_chart(fig, use_container_width=True)

# -------------------------------------------------------
# Daylight Analysis
# -------------------------------------------------------

st.divider()
st.header("Daylight Analysis")

col1, col2 = st.columns(2)

with col1:

    fig = px.line(
        conditions_df,
        x="timestamp",
        y="daylight_duration_hours",
        title="Daylight Duration",
    )
    fig.update_layout(template="plotly_white", height=420)
    st.plotly_chart(fig, use_container_width=True)

with col2:

    fig = px.line(
        conditions_df,
        x="timestamp",
        y="sunshine_duration_hours",
        title="Sunshine Duration",
    )
    fig.update_layout(template="plotly_white", height=420)
    st.plotly_chart(fig, use_container_width=True)

st.subheader("Daylight Progress")

fig = px.line(conditions_df, x="timestamp", y="daylight_progress_pct")
fig.update_layout(template="plotly_white", height=420)
st.plotly_chart(fig, use_container_width=True)

# -------------------------------------------------------
# Forecast Relationships
# -------------------------------------------------------

st.divider()
st.header("Forecast vs Weather Conditions")

col1, col2 = st.columns(2)

with col1:

    fig = px.scatter(
        conditions_df,
        x="temperature_c",
        y="predicted_generation_mw",
        trendline="ols",
        title="Temperature vs Forecast",
    )
    fig.update_layout(template="plotly_white", height=420)
    st.plotly_chart(fig, use_container_width=True)

with col2:

    fig = px.scatter(
        conditions_df,
        x="cloud_cover_pct",
        y="predicted_generation_mw",
        trendline="ols",
        title="Cloud Cover vs Forecast",
    )
    fig.update_layout(template="plotly_white", height=420)
    st.plotly_chart(fig, use_container_width=True)

col1, col2 = st.columns(2)

with col1:

    fig = px.scatter(
        conditions_df,
        x="shortwave_radiation",
        y="predicted_generation_mw",
        trendline="ols",
        title="Shortwave Radiation vs Forecast",
    )
    fig.update_layout(template="plotly_white", height=420)
    st.plotly_chart(fig, use_container_width=True)

with col2:

    fig = px.scatter(
        conditions_df,
        x="wind_speed_kmh",
        y="predicted_generation_mw",
        trendline="ols",
        title="Wind Speed vs Forecast",
    )
    fig.update_layout(template="plotly_white", height=420)
    st.plotly_chart(fig, use_container_width=True)

# -------------------------------------------------------
# Correlation Matrix
# -------------------------------------------------------

st.divider()
st.header("Feature Correlation")

correlation_columns = [
    "temperature_c",
    "relative_humidity_pct",
    "cloud_cover_pct",
    "wind_speed_kmh",
    "precipitation_mm",
    "shortwave_radiation",
    "direct_radiation",
    "diffuse_radiation",
    "direct_normal_irradiance",
    "daylight_duration_hours",
    "sunshine_duration_hours",
    "daylight_progress_pct",
]

corr = conditions_df[correlation_columns].corr(numeric_only=True)

fig = px.imshow(
    corr,
    text_auto=".2f",
    aspect="auto",
    color_continuous_scale="RdBu_r",
)
fig.update_layout(template="plotly_white", height=700)
st.plotly_chart(fig, use_container_width=True)

# -------------------------------------------------------
# Feature Statistics
# -------------------------------------------------------

st.divider()
st.header("Feature Statistics")

stats = conditions_df[correlation_columns].describe().T
st.dataframe(stats, use_container_width=True)

# -------------------------------------------------------
# Raw Dataset
# -------------------------------------------------------

with st.expander("View Condition Dataset"):
    st.dataframe(conditions_df, use_container_width=True, height=450)

# -------------------------------------------------------
# Download
# -------------------------------------------------------

st.download_button(
    label="Download Condition Data",
    data=conditions_df.to_csv(index=False),
    file_name="condition_analysis.csv",
    mime="text/csv",
)

# -------------------------------------------------------
# Footer
# -------------------------------------------------------

st.caption(
    "GridSight • Weather, irradiance and daylight features for the "
    "current forecast window."
)