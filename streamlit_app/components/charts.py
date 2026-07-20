"""
Reusable Plotly chart builders.

Plotly only, per project requirements -- no matplotlib/seaborn/altair
anywhere in this app.
"""

import pandas as pd
import plotly.graph_objects as go

from config import PRIMARY_COLOR, ACCENT_COLOR


def forecast_line_chart(
    forecast_df: pd.DataFrame,
    historical_df: pd.DataFrame = None,
) -> go.Figure:
    """Overlay historical generation with forecast values."""

    fig = go.Figure()

    if historical_df is not None and not historical_df.empty:
        fig.add_trace(
            go.Scatter(
                x=historical_df["timestamp"],
                y=historical_df["solar_generation_mw"],
                mode="lines",
                name="Actual",
                line=dict(color=PRIMARY_COLOR, width=2),
            )
        )

    if forecast_df is not None and not forecast_df.empty:
        fig.add_trace(
            go.Scatter(
                x=forecast_df["timestamp"],
                y=forecast_df["predicted_generation_mw"],
                mode="lines",
                name="Forecast",
                line=dict(color=ACCENT_COLOR, width=2, dash="dash"),
            )
        )

    fig.update_layout(
        template="plotly_white",
        margin=dict(l=10, r=10, t=30, b=10),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            x=0,
        ),
        xaxis_title=None,
        yaxis_title="Generation (MW)",
        height=380,
    )

    return fig


def daily_trend_chart(forecast_df: pd.DataFrame) -> go.Figure:
    """
    Shows the forecast profile across the available forecast horizon.
    """

    if forecast_df is None or forecast_df.empty:
        return go.Figure()

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=forecast_df["timestamp"],
            y=forecast_df["predicted_generation_mw"],
            mode="lines+markers",
            name="Forecast",
            line=dict(color=PRIMARY_COLOR, width=3),
        )
    )

    fig.update_layout(
        template="plotly_white",
        margin=dict(l=10, r=10, t=30, b=10),
        xaxis_title="Time",
        yaxis_title="Generation (MW)",
        height=320,
    )

    return fig