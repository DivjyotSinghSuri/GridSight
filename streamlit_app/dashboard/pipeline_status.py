import streamlit as st


def render_pipeline_status():
    st.title("⚙️ Pipeline Status")
    st.caption("Operational health and freshness of the GridSight ELT + forecasting pipeline.")

    try:
        from ..components.utils import (
            format_timestamp,
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

        forecast_horizon_df = run_query(
            f"SELECT MAX(forecast_timestamp) AS latest_forecast, "
            f"COUNT(*) AS forecast_horizon "
            f"FROM {FORECAST_TABLE} "
            f"WHERE forecast_timestamp = (SELECT MAX(forecast_timestamp) FROM {FORECAST_TABLE})"
        )
        latest_forecast_ts = (
            forecast_horizon_df.iloc[0]["latest_forecast"]
            if not forecast_horizon_df.empty
            else None
        )
        forecast_horizon = (
            int(forecast_horizon_df.iloc[0]["forecast_horizon"])
            if not forecast_horizon_df.empty and forecast_horizon_df.iloc[0]["forecast_horizon"] is not None
            else 0
        )

        forecast_count_df = run_query(f"SELECT COUNT(*) AS n FROM {FORECAST_TABLE}")
        forecast_count = int(forecast_count_df.iloc[0]["n"]) if not forecast_count_df.empty else 0

        latest_weather = load_latest_weather()
        latest_weather_ts = latest_weather.get("timestamp") if not latest_weather.empty else None

        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Database", "🟢 Connected" if db_ok else "🔴 Unavailable")
            st.metric("Forecast Records", f"{forecast_count:,}")
        with c2:
            st.metric("Forecast Horizon", f"{forecast_horizon:,}" if forecast_horizon > 0 else "—")
            st.metric("Latest Forecast", format_timestamp(latest_forecast_ts))
        with c3:
            st.metric(
                "Last Pipeline Run",
                format_timestamp(last_run_val) if last_run_val is not None else "No runs yet",
            )
            st.metric("Latest Weather", format_timestamp(latest_weather_ts))
            st.metric("Model Version", metrics.get("model_version", "—"))

    except Exception:
        st.info("Pipeline status information is unavailable in this environment.")
