"""
Predictions page.

Displays the latest 24-hour solar generation forecast produced by the
GridSight forecasting pipeline: KPI summary, forecast timeline,
forecast vs. actual (where available), and the raw forecast table.
"""

import streamlit as st
import plotly.express as px

from utils.queries import (
    load_latest_forecast,
    load_latest_forecast_kpis,
    load_latest_forecast_vs_actual,
    load_model_evaluation_metrics,
)


st.set_page_config(page_title="Predictions", page_icon="📈", layout="wide")

st.title("📈 Solar Generation Forecast")

# -------------------------------------------------------------------
# Load Data
# -------------------------------------------------------------------

forecast_df = load_latest_forecast()

if forecast_df.empty:
    st.warning("No forecast data available.")
    st.stop()

kpis = load_latest_forecast_kpis().iloc[0]
model_metrics = load_model_evaluation_metrics().iloc[0]
actual_df = load_latest_forecast_vs_actual()

last_update = forecast_df["forecast_created_at"].max()
forecast_start = forecast_df["forecast_timestamp"].min()
forecast_end = forecast_df["forecast_timestamp"].max()
model_name = forecast_df["model_name"].iloc[0]
model_version = forecast_df["model_version"].iloc[0]

st.caption(
    f"""
Latest forecast generated on **{last_update:%d %b %Y • %H:%M}**

Forecast horizon: **{forecast_start:%d %b %H:%M}**
→ **{forecast_end:%d %b %H:%M}**
"""
)

st.divider()

# -------------------------------------------------------------------
# KPI Cards
# -------------------------------------------------------------------

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Forecast", f"{kpis.total_generation:,.1f} MW")

with col2:
    st.metric("Peak Output", f"{kpis.peak_generation:,.1f} MW")

with col3:
    st.metric("Peak Time", str(kpis.peak_hour))

with col4:
    # WAPE comes from the full-history evaluation metrics, so this
    # number always reflects real model performance — never hardcoded.
    wape_display = (
        f"{model_metrics.wape:.2f}%"
        if model_metrics.n_observations and model_metrics.wape is not None
        else "N/A"
    )
    st.metric("Model WAPE", wape_display)

st.divider()

# -------------------------------------------------------------------
# Forecast Summary
# -------------------------------------------------------------------

st.subheader("Forecast Summary")

st.info(
    f"""
The latest forecast estimates **{kpis.total_generation:,.1f} MW** of solar
generation across the next **{int(kpis.forecast_hours)} hours**.

Peak generation is expected to reach **{kpis.peak_generation:,.1f} MW**
around **{kpis.peak_hour}**.

Forecasts are generated using the production **{model_name} ({model_version})**
model and refreshed automatically after the daily data ingestion pipeline.
"""
)

# -------------------------------------------------------------------
# Forecast Line Chart
# -------------------------------------------------------------------

fig = px.line(
    forecast_df,
    x="forecast_timestamp",
    y="predicted_generation_mw",
    title="Forecasted Solar Generation",
)

fig.update_traces(line_width=3)

fig.update_layout(
    template="plotly_white",
    hovermode="x unified",
    height=520,
    xaxis_title="Time",
    yaxis_title="Generation (MW)",
    margin=dict(l=20, r=20, t=60, b=20),
)

st.plotly_chart(
    fig,
    use_container_width=True,
    config={"displayModeBar": False},
)

st.divider()

# -------------------------------------------------------------------
# Secondary Charts
# -------------------------------------------------------------------

left, right = st.columns(2)

with left:

    st.subheader("Forecast vs Actual")

    if actual_df.empty:

        st.info("Actual generation data not yet available for this window.")

    else:

        fig_actual = px.line(
            actual_df,
            x="forecast_timestamp",
            y=[
                "predicted_generation_mw",
                "actual_generation_mw",
            ],
            labels={
                "value": "Generation (MW)",
                "variable": "Series",
            },
        )

        fig_actual.for_each_trace(
            lambda trace: trace.update(
                name=trace.name.replace(
                    "predicted_generation_mw",
                    "Predicted",
                ).replace(
                    "actual_generation_mw",
                    "Actual",
                )
            )
        )

        fig_actual.update_layout(
            template="plotly_white",
            hovermode="x unified",
            xaxis_title="Time",
            yaxis_title="Generation (MW)",
            margin=dict(l=20, r=20, t=40, b=20),
        )

        st.plotly_chart(
            fig_actual,
            use_container_width=True,
            config={"displayModeBar": False},
        )

with right:

    st.subheader("Hourly Forecast")

    fig_bar = px.bar(
        forecast_df,
        x="forecast_timestamp",
        y="predicted_generation_mw",
    )

    fig_bar.update_layout(
        template="plotly_white",
        xaxis_title="Time",
        yaxis_title="Generation (MW)",
        margin=dict(l=20, r=20, t=40, b=20),
    )

    st.plotly_chart(
        fig_bar,
        use_container_width=True,
        config={"displayModeBar": False},
    )

st.divider()

# -------------------------------------------------------------------
# Forecast Table
# -------------------------------------------------------------------

st.subheader("Forecast Data")

display_df = forecast_df.rename(
    columns={
        "forecast_created_at": "Forecast Run",
        "forecast_timestamp": "Forecast Time",
        "predicted_generation_mw": "Predicted Generation (MW)",
        "model_name": "Model",
        "model_version": "Version",
    }
)

st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True,
)