import plotly.express as px
import plotly.graph_objects as go


def apply_layout(fig, title=None):
    """
    Apply a consistent GridSight theme.
    """

    fig.update_layout(
        title=title,
        template="plotly_white",
        height=450,
        margin=dict(l=20, r=20, t=50, b=20),
        legend_title=None,
        hovermode="x unified"
    )

    fig.update_xaxes(showgrid=True)

    fig.update_yaxes(showgrid=True)

    return fig


def line_chart(df, x, y, title):
    fig = px.line(
        df,
        x=x,
        y=y
    )

    return apply_layout(fig, title)


def area_chart(df, x, y, title):
    fig = px.area(
        df,
        x=x,
        y=y
    )

    return apply_layout(fig, title)


def bar_chart(df, x, y, title):
    fig = px.bar(
        df,
        x=x,
        y=y
    )

    return apply_layout(fig, title)


def scatter_chart(df, x, y, title):
    fig = px.scatter(
        df,
        x=x,
        y=y
    )

    return apply_layout(fig, title)


def dual_axis_chart(
    df,
    x,
    y1,
    y2,
    y1_name,
    y2_name,
    title,
):
    """
    Dual-axis chart for comparing two metrics.
    """

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df[x],
            y=df[y1],
            name=y1_name,
            mode="lines",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=df[x],
            y=df[y2],
            name=y2_name,
            mode="lines",
            yaxis="y2",
        )
    )

    fig.update_layout(
        title=title,
        template="plotly_white",
        hovermode="x unified",
        height=450,
        margin=dict(l=20, r=20, t=50, b=20),
        yaxis=dict(title=y1_name),
        yaxis2=dict(
            title=y2_name,
            overlaying="y",
            side="right",
        ),
    )

    return fig