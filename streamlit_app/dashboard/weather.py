import streamlit as st
import plotly.express as px

from ..components.utils import load_latest_weather, run_query
from ..config import WEATHER_VIEW


def render_weather():
    st.title("🌤️ Weather")
    st.caption("Latest meteorological observations and hourly trends.")

    with st.spinner("Loading latest weather..."):
        try:
            latest = load_latest_weather()
        except Exception:
            latest = None

    if latest is None or latest.empty:
        st.info("No latest weather observations available.")
    else:
        c1, c2, c3, c4 = st.columns(4)

        with c1:
            st.metric("Temperature", f"{latest.get('temperature_c', '—')} °C")
            st.metric("Humidity", f"{latest.get('relative_humidity_pct', '—')} %")

        with c2:
            st.metric("Cloud Cover", f"{latest.get('cloud_cover_pct', '—')} %")
            st.metric("Wind Speed", f"{latest.get('wind_speed_kmh', '—')} km/h")

        with c3:
            st.metric("Precipitation", f"{latest.get('precipitation_mm', '—')} mm")
            st.metric("Timestamp", str(latest.get('timestamp', '—')))

        with c4:
            st.metric("Sunrise", str(latest.get('sunrise', '—')))
            st.metric("Sunset", str(latest.get('sunset', '—')))

    st.divider()
    st.subheader("Hourly Weather — Recent")

    # Load recent hourly weather for chart/table
    try:
        df = run_query(f"SELECT * FROM {WEATHER_VIEW} ORDER BY timestamp DESC LIMIT 72")
        if df is None or df.empty:
            st.info("No hourly weather history available.")
        else:
            df["timestamp"] = df["timestamp"]
            fig = px.line(df.sort_values("timestamp"), x="timestamp", y=["temperature_c", "cloud_cover_pct", "wind_speed_kmh"], labels={"value":"Value","variable":"Series","timestamp":"Time"}, title="Recent Weather Trends")
            fig.update_layout(template="plotly_white", height=480)
            st.plotly_chart(fig, width='stretch')

            st.subheader("Weather Table")
            st.dataframe(df.sort_values("timestamp"), width='stretch')

    except Exception:
        st.info("Hourly weather history unavailable.")
