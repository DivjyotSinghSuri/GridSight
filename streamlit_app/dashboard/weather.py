import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from ..components.utils import (
    format_cloud_cover,
    format_humidity,
    format_precipitation,
    format_temperature,
    format_timestamp,
    format_wind_speed,
    load_latest_weather,
    run_query,
)
from ..config import WEATHER_VIEW


def render_weather():
    st.title("🌤️ Weather")
    st.caption("Latest meteorological observations and hourly trends for the GridSight forecast environment.")

    with st.spinner("Loading latest weather observations..."):
        try:
            latest = load_latest_weather()
        except Exception:
            latest = None

    if latest is None or latest.empty:
        st.info(
            "Weather observations are not available at this time. "
            "Once the ingestion pipeline has completed, the latest metrics will be displayed here."
        )
    else:
        c1, c2, c3, c4 = st.columns(4)

        with c1:
            st.metric("Temperature", format_temperature(latest.get("temperature_c")))
            st.metric("Humidity", format_humidity(latest.get("relative_humidity_pct")))

        with c2:
            st.metric("Cloud Cover", format_cloud_cover(latest.get("cloud_cover_pct")))
            st.metric("Wind Speed", format_wind_speed(latest.get("wind_speed_kmh")))

        with c3:
            st.metric("Precipitation", format_precipitation(latest.get("precipitation_mm")))
            st.metric("Observation Time", format_timestamp(latest.get("timestamp")))

        with c4:
            st.metric("Sunrise", format_timestamp(latest.get("sunrise")))
            st.metric("Sunset", format_timestamp(latest.get("sunset")))

    st.divider()
    st.subheader("Hourly Weather Trends")

    try:
        df = run_query(f"SELECT * FROM {WEATHER_VIEW} ORDER BY timestamp DESC LIMIT 72")
        if df is None or df.empty:
            st.info(
                "Hourly weather history is not available. "
                "This section will update once hourly weather observations are loaded."
            )
        else:
            df = df.sort_values("timestamp")
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            fig = make_subplots(specs=[[{"secondary_y": True}]])

            fig.add_trace(
                go.Scatter(
                    x=df["timestamp"],
                    y=df["cloud_cover_pct"],
                    mode="lines+markers",
                    name="Cloud Cover",
                    line=dict(color="#6B7280", width=2),
                    marker=dict(size=4),
                ),
                secondary_y=False,
            )

            fig.add_trace(
                go.Scatter(
                    x=df["timestamp"],
                    y=df["temperature_c"],
                    mode="lines+markers",
                    name="Temperature",
                    line=dict(color="#F2A541", width=2),
                    marker=dict(size=4),
                ),
                secondary_y=True,
            )

            fig.add_trace(
                go.Scatter(
                    x=df["timestamp"],
                    y=df["wind_speed_kmh"],
                    mode="lines+markers",
                    name="Wind Speed",
                    line=dict(color="#2E5EAA", width=2, dash="dash"),
                    marker=dict(size=4),
                ),
                secondary_y=True,
            )

            fig.update_layout(
                template="plotly_white",
                title="Recent Weather Trends",
                margin=dict(l=10, r=10, t=40, b=10),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
                hovermode="x unified",
                height=500,
            )
            fig.update_xaxes(title_text="Time")
            fig.update_yaxes(title_text="Cloud Cover (%)", secondary_y=False)
            fig.update_yaxes(title_text="Temperature / Wind Speed", secondary_y=True)

            st.plotly_chart(fig, width='stretch')

            st.subheader("Hourly Weather Data")
            st.dataframe(df.sort_values("timestamp"), width='stretch')
    except Exception:
        st.info(
            "Hourly weather history cannot be displayed at this time. "
            "Please check back once the data source is available."
        )
