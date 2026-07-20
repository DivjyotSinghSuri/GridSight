"""
Model Insights page.

Presents full-history model evaluation: accuracy metrics computed over
every forecast that has a matching actual generation value (the full
test set — not limited to the latest run or a 24-hour window), plus
diagnostic charts explaining where and when the model performs well
or poorly.
"""

import pandas as pd
import streamlit as st
import plotly.express as px

from utils.queries import (
    load_latest_run_metadata,
    load_model_evaluation_metrics,
    load_actual_vs_predicted,
    load_forecast_error_over_time,
    load_forecast_error_by_hour,
)

st.set_page_config(
    page_title="Model Insights",
    page_icon="🔮",
    layout="wide",
)

st.title("🔮 Model Insights")
st.caption(
    "Full-history accuracy evaluation for the GridSight forecasting model."
)

# -------------------------------------------------------
# Load Data
# -------------------------------------------------------

@st.cache_data
def load_data():
    return (
        load_latest_run_metadata(),
        load_model_evaluation_metrics(),
        load_actual_vs_predicted(),
        load_forecast_error_over_time(),
        load_forecast_error_by_hour(),
    )


metadata_df, metrics_df, matched_df, error_over_time_df, error_by_hour_df = load_data()

if metadata_df.empty:
    st.warning("No forecast runs available.")
    st.stop()

metadata = metadata_df.iloc[0]
metrics = metrics_df.iloc[0]

# -------------------------------------------------------
# Current Production Model
# -------------------------------------------------------

st.header("Current Production Model")

c1, c2, c3, c4 = st.columns(4)

c1.metric("Model", metadata["model_name"])
c2.metric("Version", metadata["model_version"])
c3.metric("Latest Run", str(metadata["forecast_created_at"]))
c4.metric("Forecast Horizon", f"{int(metadata['forecast_rows'])} Hours")

st.divider()

# -------------------------------------------------------
# Evaluation Metrics (Full Test Set)
# -------------------------------------------------------

st.header("Evaluation Metrics — Full Test Set")

if not metrics["n_observations"]:

    st.info("No matched actual/forecast pairs are available yet for evaluation.")

else:

    st.caption(
        f"Computed across **{int(metrics['n_observations']):,}** forecast "
        "hours with a matching actual generation reading."
    )

    m1, m2, m3, m4, m5, m6 = st.columns(6)

    m1.metric("MAE", f"{metrics['mae']:.2f} MW")
    m2.metric("RMSE", f"{metrics['rmse']:.2f} MW")
    m3.metric(
        "WAPE",
        f"{metrics['wape']:.2f}%" if metrics["wape"] is not None else "N/A",
    )
    m4.metric(
        "MAPE",
        f"{metrics['mape']:.2f}%" if metrics["mape"] is not None else "N/A",
    )
    m5.metric("Bias", f"{metrics['bias']:+.2f} MW")
    m6.metric(
        "R²",
        f"{metrics['r_squared']:.3f}" if pd.notna(metrics["r_squared"]) else "N/A",
    )

st.divider()

# -------------------------------------------------------
# Actual vs Predicted
# -------------------------------------------------------

st.header("Actual vs Predicted")

if matched_df.empty:

    st.info("Actual generation data is not available yet for evaluation.")

else:

    left, right = st.columns(2)

    with left:

        st.subheader("Predicted vs Actual Generation")

        fig = px.scatter(
            matched_df,
            x="actual_generation_mw",
            y="predicted_generation_mw",
            trendline="ols",
            labels={
                "actual_generation_mw": "Actual (MW)",
                "predicted_generation_mw": "Predicted (MW)",
            },
        )

        fig.update_layout(template="plotly_white", height=450)

        st.plotly_chart(fig, use_container_width=True)

    with right:

        st.subheader("Residual Distribution")

        residuals = matched_df.assign(
            residual=(
                matched_df["predicted_generation_mw"]
                - matched_df["actual_generation_mw"]
            )
        )

        fig = px.histogram(
            residuals,
            x="residual",
            nbins=30,
            labels={"residual": "Prediction Error (MW)"},
        )

        fig.update_layout(template="plotly_white", height=450)

        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Forecast Timeline: Predicted vs Actual")

    fig = px.line(
        matched_df,
        x="forecast_timestamp",
        y=["predicted_generation_mw", "actual_generation_mw"],
        labels={"value": "Generation (MW)", "variable": "Series"},
    )

    fig.for_each_trace(
        lambda trace: trace.update(
            name=trace.name.replace(
                "predicted_generation_mw", "Predicted"
            ).replace(
                "actual_generation_mw", "Actual"
            )
        )
    )

    fig.update_layout(
        template="plotly_white",
        hovermode="x unified",
        height=480,
    )

    st.plotly_chart(fig, use_container_width=True)

st.divider()

# -------------------------------------------------------
# Error Trends
# -------------------------------------------------------

st.header("Forecast Error Trends")

if error_over_time_df.empty:

    st.info("Not enough matched history to chart error trends yet.")

else:

    left, right = st.columns(2)

    with left:

        st.subheader("Daily Mean Absolute Error")

        fig = px.bar(
            error_over_time_df,
            x="date",
            y="mean_abs_error",
            labels={"date": "Date", "mean_abs_error": "Mean Abs. Error (MW)"},
        )

        fig.update_layout(template="plotly_white", height=420)

        st.plotly_chart(fig, use_container_width=True)

    with right:

        st.subheader("Error by Hour of Day")

        fig = px.bar(
            error_by_hour_df,
            x="hour",
            y="mean_abs_error",
            labels={"hour": "Hour of Day", "mean_abs_error": "Mean Abs. Error (MW)"},
        )

        fig.update_layout(template="plotly_white", height=420)

        st.plotly_chart(fig, use_container_width=True)

st.divider()

# -------------------------------------------------------
# Data Explorer
# -------------------------------------------------------

st.header("Evaluation Data Explorer")

if not matched_df.empty:

    st.dataframe(
        matched_df,
        use_container_width=True,
        hide_index=True,
        height=420,
    )

    st.download_button(
        label="📥 Download Evaluation Data",
        data=matched_df.to_csv(index=False),
        file_name="gridsight_model_evaluation.csv",
        mime="text/csv",
    )

st.divider()

st.caption(
    """
GridSight • Renewable Energy Forecasting Platform

Data Sources: Open-Meteo Weather • Open-Meteo Solar • ENTSO-E

Evaluation metrics are computed over every forecast with a matching
actual reading (the full test set), using the production Ridge
Regression model.
"""
)