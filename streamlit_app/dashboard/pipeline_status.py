import streamlit as st


def render_pipeline_status():
    st.title("⚙️ Pipeline Status")
    st.caption("Operational health and freshness of the GridSight ELT + forecasting pipeline.")

    try:
        from ..components.utils import (
            load_latest_daylight,
            load_metrics,
            database_is_reachable,
            run_query,
            load_latest_weather,
        )
        from ..config import FORECAST_TABLE

        metrics = load_metrics()
        db_ok = database_is_reachable()
        last_run = run_query(f"SELECT MAX(forecast_created_at) AS last_run FROM {FORECAST_TABLE}")
        last_run_val = last_run.iloc[0]["last_run"] if not last_run.empty else None

        forecast_count_df = run_query(f"SELECT COUNT(*) AS n FROM {FORECAST_TABLE}")
        forecast_count = int(forecast_count_df.iloc[0]["n"]) if not forecast_count_df.empty else 0

        latest_weather = load_latest_weather()
        latest_weather_ts = latest_weather.get("timestamp") if not latest_weather.empty else None

        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Database", "🟢 Connected" if db_ok else "🔴 Unavailable")
            st.metric("Last Pipeline Run", str(last_run_val) if last_run_val is not None else "No runs yet")
        with c2:
            st.metric("Forecasts Available", "Yes" if forecast_count > 0 else "No")
            st.metric("Forecast Records", f"{forecast_count:,}")
        with c3:
            st.metric("Latest Weather", str(latest_weather_ts) if latest_weather_ts is not None else "Unavailable")
            st.metric("Model Version", metrics.get("model_version", "—"))

    except Exception:
        st.info("Pipeline status information is unavailable in this environment.")
