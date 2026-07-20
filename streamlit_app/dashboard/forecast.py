import streamlit as st
import pandas as pd

from ..components.metric_cards import metric_row
from ..components.charts import (
    forecast_line_chart,
    daily_trend_chart
)
from ..components.utils import (
    load_latest_forecast_window,
    load_metrics
)


def render_forecasts():
    st.title("📈 Forecasts")

    forecast_df = load_latest_forecast_window()
    metrics = load_metrics()

    if forecast_df.empty:
        st.warning("No forecast data available.")
        return

    prediction_col = "predicted_generation_mw"

    latest_forecast = forecast_df[prediction_col].iloc[0]
    peak_forecast = forecast_df[prediction_col].max()
    avg_forecast = forecast_df[prediction_col].mean()
    horizon = len(forecast_df)

    metric_row(
        [
            ("Current Forecast", f"{latest_forecast:.2f} MW"),
            ("Peak Forecast", f"{peak_forecast:.2f} MW"),
            ("Average Output", f"{avg_forecast:.2f} MW"),
            ("Std Dev", f"{forecast_df[prediction_col].std():.2f} MW"),
            ("Forecast Horizon", f"{horizon} Hours"),
        ]
    )

    st.divider()
    
    st.subheader("Forecast vs Actual")

    fig = forecast_line_chart(forecast_df)
    st.plotly_chart(fig, width='stretch')

    st.divider()

    st.subheader("24-Hour Forecast Profile")

    fig = daily_trend_chart(forecast_df)
    st.plotly_chart(fig, width='stretch')

    st.divider()

    st.subheader("Forecast Statistics")

    c1, c2 = st.columns(2)

    with c1:
        st.metric(
            "Maximum Prediction",
            f"{forecast_df[prediction_col].max():.2f} MW",
        )

        st.metric(
            "Minimum Prediction",
            f"{forecast_df[prediction_col].min():.2f} MW",
        )

    with c2:
        st.metric(
            "Average Prediction",
            f"{forecast_df[prediction_col].mean():.2f} MW",
        )

        total_energy = forecast_df[prediction_col].sum()

        st.metric(
            "Total Forecast Energy",
            f"{total_energy:.2f} MWh",
        )
        
    st.divider()

    st.subheader("Forecast Data")

    display_df = forecast_df.copy()

    display_df = display_df.rename(
        columns={
            "timestamp": "Timestamp",
            "predicted_generation_mw": "Forecast (MW)"
        }
    )

    st.dataframe(
        display_df,
        width='stretch',
        hide_index=True,
    )

    # Download CSV
    csv_bytes = display_df.to_csv(index=False).encode('utf-8')
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