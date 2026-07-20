"""Overview page -- executive summary."""
import streamlit as st

from components.metric_cards import metric_row
from components.charts import forecast_line_chart, daily_trend_chart
from components.utils import (
    load_latest_forecast_window,
    load_historical_generation,
    load_latest_weather,
    load_latest_daylight,
    load_metrics,
    today_utc,
)


def render_overview() -> None:
    st.title("Overview")

    forecast_df = load_latest_forecast_window(hours=24)
    historical_df = load_historical_generation(days=30)
    metrics = load_metrics()

    if forecast_df.empty:
        st.warning(
            "No forecast data available yet in `gold_forecasts`. "
            "Run the inference pipeline (or the Airflow DAG) first."
        )
    else:
        st.caption(
            "⚠️ Forecasts shown here are produced by batch-scoring the "
            "latest available historical timestamps with a full lag/rolling "
            "history, not by a true future-weather-driven forecast. A "
            "dedicated recursive inference pipeline for genuine next-24h "
            "forecasting is planned as a follow-up."
        )

    # "Today" window: prefer rows matching today's UTC calendar date;
    # fall back to the most recent 24 observed hours if today's actuals
    # haven't landed yet (ingestion runs on a ~1-day lag).
    if not historical_df.empty:
        today_rows = historical_df[historical_df["timestamp"].dt.date == today_utc()]
        today_window = today_rows if not today_rows.empty else historical_df.tail(24)
    else:
        today_window = historical_df

    current_value = (
        f"{forecast_df['predicted_generation_mw'].iloc[-1]:.1f} MW"
        if not forecast_df.empty else "—"
    )
    peak_value = (
        f"{today_window['solar_generation_mw'].max():.1f} MW"
        if not today_window.empty else "—"
    )
    today_energy = (
        f"{today_window['solar_generation_mw'].sum():.0f} MWh"
        if not today_window.empty else "—"
    )

    metric_row([
        {"label": "Current Forecast", "value": current_value},
        {"label": "Today's Peak Generation", "value": peak_value},
        {"label": "Today's Energy", "value": today_energy},
        {"label": "Test WAPE", "value": f"{metrics.get('test_wape_pct', 0):.2f}%"},
        {"label": "Model", "value": metrics.get("model_name", "Ridge Regression")},
    ])

    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Forecast — Latest Window")
        st.plotly_chart(forecast_line_chart(forecast_df), use_container_width=True)
    with col2:
        st.subheader("Historical vs. Forecast")
        st.plotly_chart(
            forecast_line_chart(forecast_df, historical_df.tail(24 * 3)),
            use_container_width=True,
        )

    st.subheader("Daily Generation Trend")
    st.plotly_chart(daily_trend_chart(historical_df), use_container_width=True)

    st.divider()
    st.subheader("Latest Weather")

    weather = load_latest_weather()
    daylight = load_latest_daylight()

    w1, w2, w3, w4, w5 = st.columns(5)
    w1.metric("Cloud Cover", f"{weather['cloud_cover_pct']:.0f}%" if not weather.empty else "—")
    w2.metric("Temperature", f"{weather['temperature_c']:.1f}°C" if not weather.empty else "—")
    w3.metric("Wind Speed", f"{weather['wind_speed_kmh']:.1f} km/h" if not weather.empty else "—")
    w4.metric("Sunrise", str(daylight["sunrise"]) if not daylight.empty else "—")
    w5.metric("Sunset", str(daylight["sunset"]) if not daylight.empty else "—")