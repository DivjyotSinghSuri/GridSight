import streamlit as st
import pandas as pd

from ..components.metric_cards import metric_row
from ..components.charts import (
    forecast_line_chart,
    daily_trend_chart
)
from ..components.utils import (
    format_energy,
    format_percentage,
    format_power,
    format_timestamp,
    load_latest_forecast_window,
    load_metrics,
)


def render_forecasts():
    st.title("📈 Forecasts")

    forecast_df = load_latest_forecast_window()
    metrics = load_metrics()

    if forecast_df.empty:
        st.info(
            "Forecast data is not available at the moment. "
            "Once the forecasting pipeline completes, predictions will be visible here."
        )
        return

    prediction_col = "predicted_generation_mw"

    latest_forecast = forecast_df[prediction_col].iloc[0]
    peak_forecast = forecast_df[prediction_col].max()
    avg_forecast = forecast_df[prediction_col].mean()
    horizon = len(forecast_df)

    metric_row(
        [
            ("Current Forecast", format_power(latest_forecast)),
            ("Peak Forecast", format_power(peak_forecast)),
            ("Average Output", format_power(avg_forecast)),
            ("Std Dev", format_power(forecast_df[prediction_col].std())),
            ("Forecast Horizon", f"{horizon} Hours"),
        ]
    )

    st.divider()
    st.subheader("Forecast Metadata")

    window_start = forecast_df["timestamp"].min()
    window_end = forecast_df["timestamp"].max()

    meta_c1, meta_c2, meta_c3 = st.columns(3)
    with meta_c1:
        st.metric("Model", metrics.get("model_name", "—"))
        st.metric("Model Version", metrics.get("model_version", "—"))

    with meta_c2:
        st.metric("Forecast Horizon", f"{horizon} Hours")
        st.metric(
            "Forecast Window",
            f"{format_timestamp(window_start)} – {format_timestamp(window_end)}",
        )

    with meta_c3:
        st.metric("Test WAPE", format_percentage(metrics.get("wape", metrics.get("test_wape_pct", None))))
        st.metric("Latest Forecast", format_timestamp(window_end))

    st.divider()
    st.subheader("Forecast Profile")

    fig = forecast_line_chart(forecast_df)
    fig.update_layout(title_text="Forecast vs Actual")
    st.plotly_chart(fig, width='stretch')

    st.divider()

    st.subheader("24-Hour Forecast Profile")

    fig = daily_trend_chart(forecast_df)
    fig.update_layout(title_text="24-Hour Forecast Profile")
    st.plotly_chart(fig, width='stretch')

    st.divider()

    st.subheader("Forecast Statistics")

    total_energy = forecast_df[prediction_col].sum()
    c1, c2 = st.columns(2)

    with c1:
        st.metric(
            "Maximum Prediction",
            format_power(forecast_df[prediction_col].max()),
        )

        st.metric(
            "Minimum Prediction",
            format_power(forecast_df[prediction_col].min()),
        )

    with c2:
        st.metric(
            "Average Prediction",
            format_power(forecast_df[prediction_col].mean()),
        )

        st.metric(
            "Total Forecast Energy",
            format_energy(total_energy),
        )

    st.divider()

    st.subheader("Forecast Data")

    display_df = forecast_df.copy()
    display_df["timestamp"] = pd.to_datetime(display_df["timestamp"])
    display_df = display_df.rename(
        columns={
            "timestamp": "Timestamp",
            "predicted_generation_mw": "Forecast (MW)",
        }
    )
    display_df["Timestamp"] = display_df["Timestamp"].dt.strftime("%Y-%m-%d %H:%M")

    st.dataframe(
        display_df,
        width='stretch',
        hide_index=True,
    )

    csv_bytes = display_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Download Forecast CSV",
        data=csv_bytes,
        file_name="forecast_window.csv",
        mime="text/csv",
    )

    st.caption(
        f"""
    Model: Ridge Regression

    Forecast Window: {forecast_df['timestamp'].min()}
    to
    {forecast_df['timestamp'].max()}

    Test WAPE: {metrics.get('wape', metrics.get('test_wape_pct', 0)):.2f}%
    """
    )