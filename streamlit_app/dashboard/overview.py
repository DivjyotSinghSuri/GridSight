"""
Overview page for GridSight.

Executive dashboard showing:
- Pipeline status
- KPI metrics
- Forecast summary
- Historical generation

Read-only dashboard.
"""

import streamlit as st
import pandas as pd

from ..components.metric_cards import metric_row
from ..components.charts import (
    forecast_line_chart,
    daily_trend_chart,
)

from ..components.utils import (
    format_cloud_cover,
    format_energy,
    format_humidity,
    format_percentage,
    format_power,
    format_precipitation,
    format_temperature,
    format_timestamp,
    format_wind_speed,
    load_latest_forecast_window,
    load_historical_generation,
    load_latest_weather,
    load_latest_daylight,
    load_metrics,
    today_utc,
    last_pipeline_run_utc,
)


# ----------------------------------------------------------
# Helpers
# ----------------------------------------------------------

def _safe_metric(value, suffix=""):
    if value is None:
        return "—"

    try:
        if pd.isna(value):
            return "—"
    except Exception:
        pass

    return f"{value}{suffix}"


def _status_banner(forecast_df, historical_df):
    if forecast_df.empty:
        st.warning(
            "Forecast data is not yet available. "
            "Once the forecasting pipeline completes, the forecast overview will update automatically."
        )

    elif historical_df.empty:
        st.warning(
            "Historical generation data is currently unavailable. "
            "This section will populate once the historical pipeline refreshes."
        )

    else:
        st.success("Production pipeline healthy.")


# ----------------------------------------------------------
# Main Page
# ----------------------------------------------------------

def render_overview():

    try:

        st.title("Overview")

        forecast_df = load_latest_forecast_window(hours=24)
        historical_df = load_historical_generation(days=30)
        weather = load_latest_weather()
        daylight = load_latest_daylight()
        metrics = load_metrics()


    except Exception as e:
        st.exception(e)
        return

    # ------------------------------------------------------
    # Today's Window
    # ------------------------------------------------------

    if not historical_df.empty:

        today_rows = historical_df[
            historical_df["timestamp"].dt.date == today_utc()
        ]

        if today_rows.empty:
            today_rows = historical_df.tail(24)

    else:
        today_rows = pd.DataFrame()

    # ------------------------------------------------------
    # KPI Calculations
    # ------------------------------------------------------

    if not forecast_df.empty:
        current_forecast = format_power(forecast_df["predicted_generation_mw"].iloc[-1])
        forecast_peak = format_power(forecast_df["predicted_generation_mw"].max())
    else:
        current_forecast = "No Forecast"
        forecast_peak = "No Forecast"

    if not today_rows.empty:
        today_peak = format_power(today_rows["solar_generation_mw"].max())
        today_energy = format_energy(today_rows["solar_generation_mw"].sum())
    else:
        today_peak = "—"
        today_energy = "—"

    metric_row(
        [
            {
                "label": "Current Forecast",
                "value": current_forecast,
            },
            {
                "label": "Peak Forecast (Today)",
                "value": today_peak,
            },
            {
                "label": "Total Forecast Energy (Today)",
                "value": today_energy,
            },
            {
                "label": "Model WAPE",
                "value": format_percentage(metrics.get("test_wape_pct", None)),
            },
            {
                "label": "Active Model",
                "value": metrics.get("model_name", "Ridge Regression"),
            },
            {
                "label": "Model Version",
                "value": metrics.get("model_version", "v1.0"),
            },
            {
                "label": "Forecast Generated At",
                "value": last_pipeline_run_utc(),
            },
        ]
    )

    st.divider()

    # ------------------------------------------------------
    # Forecast Section
    # ------------------------------------------------------

    st.subheader("Forecast Overview")

    left, right = st.columns([2, 1])

    with left:

        if forecast_df.empty:

            st.info(
                "Forecast results are not yet available. "
                "Please check back after the next pipeline run."
            )

        else:

            fig = forecast_line_chart(forecast_df)
            fig.update_layout(title_text="Forecast Overview")

            st.plotly_chart(
                fig,
                width='stretch',
                key="overview_forecast_chart",
            )

    with right:

        st.markdown("#### Forecast Summary")

        st.metric(
            "Current",
            current_forecast,
        )

        st.metric(
            "Peak Forecast",
            forecast_peak,
        )

        st.metric(
            "Forecast Horizon",
            f"{len(forecast_df)} Hours",
        )

        st.metric(
            "Production Model",
            metrics.get(
                "model_name",
                "Ridge Regression",
            ),
        )

    st.divider()
    
    # ------------------------------------------------------
    # Historical vs Forecast
    # ------------------------------------------------------

    st.subheader("Historical vs Forecast")

    if historical_df.empty and forecast_df.empty:
        st.info(
            "Historical and forecast data are not available at this time. "
            "Once the data warehouse is refreshed, this overview will display the latest trends."
        )

    else:

        fig = forecast_line_chart(
            forecast_df=forecast_df,
            historical_df=historical_df.tail(72)
            if not historical_df.empty
            else None,
        )
        fig.update_layout(title_text="Historical vs Forecast")

        st.plotly_chart(
            fig,
            width='stretch',
            key="overview_historical_forecast",
        )

    st.divider()

    # ------------------------------------------------------
    # Daily Generation Trend
    # ------------------------------------------------------

    st.subheader("Daily Generation Trend")

    if historical_df.empty:
        st.info(
            "Historical generation data is not available. "
            "This chart will update after the next historical ingestion completes."
        )

    else:

        fig = daily_trend_chart(historical_df)
        fig.update_layout(title_text="Daily Generation Trend")

        st.plotly_chart(
            fig,
            width='stretch',
            key="overview_daily_generation",
        )

    st.divider()

    # ------------------------------------------------------
    # Weather Snapshot
    # ------------------------------------------------------

    st.subheader("Latest Weather")

    c1, c2, c3, c4 = st.columns(4)

    if weather.empty:

        for col in (c1, c2, c3, c4):
            with col:
                st.metric("Unavailable", "—")

    else:

        with c1:
            st.metric("Temperature", format_temperature(weather.get("temperature_c")))
            st.metric("Humidity", format_humidity(weather.get("relative_humidity_pct")))

        with c2:
            st.metric("Cloud Cover", format_cloud_cover(weather.get("cloud_cover_pct")))
            st.metric("Wind Speed", format_wind_speed(weather.get("wind_speed_kmh")))

        with c3:
            st.metric("Precipitation", format_precipitation(weather.get("precipitation_mm")))
            st.metric("Timestamp", format_timestamp(weather.get("timestamp")))

        with c4:

            if not daylight.empty:

                st.metric(
                    "Sunrise",
                    str(daylight.get("sunrise", "—")),
                )

                st.metric(
                    "Sunset",
                    str(daylight.get("sunset", "—")),
                )

            else:

                st.metric("Sunrise", "—")
                st.metric("Sunset", "—")

    st.divider()

    # ------------------------------------------------------
    # Daylight Summary
    # ------------------------------------------------------

    st.subheader("Daylight Summary")

    if daylight.empty:
        st.info(
            "Daylight summary data is currently unavailable. "
            "It will appear once the daylight dataset is populated."
        )

    else:

        d1, d2 = st.columns(2)

        with d1:

            st.metric(
                "Daylight Duration",
                _safe_metric(
                    daylight.get("daylight_duration_hours"),
                    " hrs",
                ),
            )

        with d2:

            st.metric(
                "Sunshine Duration",
                _safe_metric(
                    daylight.get("sunshine_duration_hours"),
                    " hrs",
                ),
            )

    st.divider()

    # ------------------------------------------------------
    # Dataset Summary
    # ------------------------------------------------------

    st.subheader("Dataset Summary")

    s1, s2, s3 = st.columns(3)

    with s1:

        st.metric(
            "Historical Records",
            f"{len(historical_df):,}",
        )

    with s2:

        st.metric(
            "Forecast Records",
            f"{len(forecast_df):,}",
        )

    with s3:

        st.metric(
            "Model Version",
            metrics.get(
                "model_version",
                "v1.0",
            ),
        )

    st.caption(
        "GridSight is a read-only dashboard. "
        "This page visualizes data produced by the daily Airflow pipeline "
        "and stored in DuckDB."
    )