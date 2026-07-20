"""
Data access layer for the GridSight Streamlit dashboard.

This module is the single source of truth for every SQL statement
executed against the DuckDB warehouse, and for the light aggregation
logic (e.g. model accuracy metrics) that is derived directly from
query results. Streamlit pages must never write SQL or perform
warehouse-level aggregation themselves — they call functions defined
here and work only with the returned pandas DataFrames.
"""

import pandas as pd

from .database import get_connection


# ============================================================
# SHARED SQL FRAGMENTS
# ============================================================

# Resolves the most recent forecast run and exposes it as the
# `latest_forecast` CTE, so downstream queries can just `SELECT FROM
# latest_forecast` instead of repeating the "latest run" subquery.
LATEST_FORECAST_RUN_CTE = """
WITH latest_run AS (
    SELECT MAX(forecast_created_at) AS latest
    FROM gold_forecasts
),
latest_forecast AS (
    SELECT *
    FROM gold_forecasts
    WHERE forecast_created_at = (SELECT latest FROM latest_run)
)
"""


def _run_query(query: str) -> pd.DataFrame:
    """Executes a SQL statement against DuckDB and returns a DataFrame."""
    with get_connection() as con:
        return con.execute(query).df()


# ============================================================
# PREDICTIONS PAGE — latest 24-hour forecast
# ============================================================

def load_latest_forecast() -> pd.DataFrame:
    """Returns every row of the most recent forecast run, ordered by time."""
    query = f"""
    {LATEST_FORECAST_RUN_CTE}
    SELECT
        forecast_created_at,
        forecast_timestamp,
        predicted_generation_mw,
        model_name,
        model_version
    FROM latest_forecast
    ORDER BY forecast_timestamp;
    """
    return _run_query(query)


def load_latest_forecast_kpis() -> pd.DataFrame:
    """Aggregated KPIs (total/avg/peak/min generation + peak hour) for the latest run."""
    query = f"""
    {LATEST_FORECAST_RUN_CTE}
    SELECT
        SUM(predicted_generation_mw) AS total_generation,
        AVG(predicted_generation_mw) AS average_generation,
        MAX(predicted_generation_mw) AS peak_generation,
        MIN(predicted_generation_mw) AS minimum_generation,
        COUNT(*) AS forecast_hours,
        (
            SELECT forecast_timestamp
            FROM latest_forecast
            ORDER BY predicted_generation_mw DESC
            LIMIT 1
        ) AS peak_hour
    FROM latest_forecast;
    """
    return _run_query(query)


def load_latest_forecast_vs_actual() -> pd.DataFrame:
    """Latest forecast joined against actual generation, for the hours where it exists."""
    query = f"""
    {LATEST_FORECAST_RUN_CTE}
    SELECT
        f.forecast_timestamp,
        f.predicted_generation_mw,
        g.solar_generation_mw AS actual_generation_mw
    FROM latest_forecast f
    INNER JOIN stg_generation g
        ON f.forecast_timestamp = g.timestamp
    ORDER BY f.forecast_timestamp;
    """
    return _run_query(query)


# ============================================================
# SHARED — latest run metadata (Model Insights + Pipeline Health)
# ============================================================

def load_latest_run_metadata() -> pd.DataFrame:
    """
    Metadata describing the most recent forecast run: model identity,
    row count, and the forecast's time window. Shared by the Model
    Insights and Pipeline Health pages to avoid duplicating this query.
    """
    query = f"""
    {LATEST_FORECAST_RUN_CTE}
    SELECT
        model_name,
        model_version,
        MAX(forecast_created_at) AS forecast_created_at,
        COUNT(*) AS forecast_rows,
        MIN(forecast_timestamp) AS forecast_start,
        MAX(forecast_timestamp) AS forecast_end
    FROM latest_forecast
    GROUP BY model_name, model_version;
    """
    return _run_query(query)


# ============================================================
# MODEL INSIGHTS PAGE — full-history model evaluation
# ============================================================

def load_actual_vs_predicted() -> pd.DataFrame:
    """
    Every forecast ever produced that has a matching actual generation
    reading. This is the model's full test set — not limited to the
    latest run or a 24-hour window.
    """
    query = """
    SELECT
        f.forecast_timestamp,
        f.predicted_generation_mw,
        g.solar_generation_mw AS actual_generation_mw
    FROM gold_forecasts f
    INNER JOIN stg_generation g
        ON f.forecast_timestamp = g.timestamp
    ORDER BY f.forecast_timestamp;
    """
    return _run_query(query)


def load_model_evaluation_metrics() -> pd.DataFrame:
    """
    Computes model accuracy metrics (MAE, RMSE, WAPE, MAPE, bias, R^2)
    across the full test set of matched predicted/actual pairs.

    The heavy lifting (the join) happens in SQL; the metric formulas
    are applied in pandas on the returned pairs, since they are simple
    row-wise arithmetic and this keeps the SQL portable and readable.
    """
    matched = load_actual_vs_predicted()

    if matched.empty:
        return pd.DataFrame([{
            "n_observations": 0,
            "mae": None,
            "rmse": None,
            "wape": None,
            "mape": None,
            "bias": None,
            "r_squared": None,
        }])

    predicted = matched["predicted_generation_mw"]
    actual = matched["actual_generation_mw"]
    error = predicted - actual
    abs_error = error.abs()

    actual_sum = actual.sum()
    wape = (abs_error.sum() / actual_sum * 100) if actual_sum else None

    # Exclude zero-actual (nighttime) rows from MAPE to avoid
    # division-by-zero blowing up the metric.
    daylight = matched[actual != 0]
    mape = (
        ((daylight["predicted_generation_mw"] - daylight["actual_generation_mw"]).abs()
         / daylight["actual_generation_mw"]).mean() * 100
        if not daylight.empty else None
    )

    correlation = predicted.corr(actual)
    r_squared = correlation ** 2 if pd.notna(correlation) else None

    return pd.DataFrame([{
        "n_observations": len(matched),
        "mae": abs_error.mean(),
        "rmse": (error ** 2).mean() ** 0.5,
        "wape": wape,
        "mape": mape,
        "bias": error.mean(),
        "r_squared": r_squared,
    }])


def load_forecast_error_over_time() -> pd.DataFrame:
    """Daily mean absolute/mean error across the full matched history."""
    query = """
    SELECT
        DATE_TRUNC('day', f.forecast_timestamp) AS date,
        AVG(ABS(f.predicted_generation_mw - g.solar_generation_mw)) AS mean_abs_error,
        AVG(f.predicted_generation_mw - g.solar_generation_mw) AS mean_error,
        COUNT(*) AS n_observations
    FROM gold_forecasts f
    INNER JOIN stg_generation g
        ON f.forecast_timestamp = g.timestamp
    GROUP BY 1
    ORDER BY 1;
    """
    return _run_query(query)


def load_forecast_error_by_hour() -> pd.DataFrame:
    """Diurnal error pattern (error by hour-of-day) across the full matched history."""
    query = """
    SELECT
        EXTRACT(HOUR FROM f.forecast_timestamp) AS hour,
        AVG(ABS(f.predicted_generation_mw - g.solar_generation_mw)) AS mean_abs_error,
        AVG(f.predicted_generation_mw) AS avg_predicted,
        AVG(g.solar_generation_mw) AS avg_actual
    FROM gold_forecasts f
    INNER JOIN stg_generation g
        ON f.forecast_timestamp = g.timestamp
    GROUP BY 1
    ORDER BY 1;
    """
    return _run_query(query)


# ============================================================
# CONDITION ANALYSIS PAGE — conditions for the latest forecast window
# ============================================================

def load_conditions_for_latest_forecast() -> pd.DataFrame:
    """
    Weather, irradiance and daylight features for the timestamps
    covered by the latest forecast run, joined with the forecasted
    generation for that same window.
    """
    query = f"""
    {LATEST_FORECAST_RUN_CTE}
    SELECT
        w.timestamp,
        f.predicted_generation_mw,
        w.temperature_c,
        w.relative_humidity_pct,
        w.cloud_cover_pct,
        w.precipitation_mm,
        w.wind_speed_kmh,
        w.shortwave_radiation,
        w.direct_radiation,
        w.diffuse_radiation,
        w.direct_normal_irradiance,
        w.daylight_duration_hours,
        w.sunshine_duration_hours,
        w.daylight_progress_pct
    FROM latest_forecast f
    INNER JOIN gold_forecast_features w
        ON f.forecast_timestamp = w.timestamp
    ORDER BY w.timestamp;
    """
    return _run_query(query)


def load_condition_summary_kpis() -> pd.DataFrame:
    """Average weather KPIs for the latest forecast window."""
    query = f"""
    {LATEST_FORECAST_RUN_CTE}
    SELECT
        AVG(w.temperature_c) AS avg_temperature,
        AVG(w.cloud_cover_pct) AS avg_cloud_cover,
        AVG(w.shortwave_radiation) AS avg_radiation,
        AVG(w.wind_speed_kmh) AS avg_wind_speed
    FROM latest_forecast f
    INNER JOIN gold_forecast_features w
        ON f.forecast_timestamp = w.timestamp;
    """
    return _run_query(query)


# ============================================================
# PIPELINE HEALTH PAGE
# ============================================================

def load_warehouse_statistics() -> pd.DataFrame:
    """Row counts for every warehouse table used by the pipeline."""
    query = """
    SELECT
        (SELECT COUNT(*) FROM gold_forecasts) AS forecast_rows,
        (SELECT COUNT(*) FROM gold_forecast_features) AS forecast_feature_rows,
        (SELECT COUNT(*) FROM gold_training_dataset) AS training_rows,
        (SELECT COUNT(*) FROM stg_weather) AS weather_rows,
        (SELECT COUNT(*) FROM stg_generation) AS generation_rows,
        (SELECT COUNT(*) FROM stg_irradiance) AS irradiance_rows,
        (SELECT COUNT(*) FROM stg_daylight) AS daylight_rows;
    """
    return _run_query(query)


def load_latest_dataset_updates() -> pd.DataFrame:
    """Latest available timestamp for each raw/staged dataset."""
    query = """
    SELECT
        (SELECT MAX(timestamp) FROM stg_weather) AS latest_weather,
        (SELECT MAX(timestamp) FROM stg_generation) AS latest_generation,
        (SELECT MAX(timestamp) FROM stg_irradiance) AS latest_irradiance,
        (SELECT MAX(date) FROM stg_daylight) AS latest_daylight,
        (SELECT MAX(forecast_created_at) FROM gold_forecasts) AS latest_forecast;
    """
    return _run_query(query)


def load_pipeline_status() -> pd.DataFrame:
    """
    Health check flags ('Healthy' / 'Missing') for every stage of the
    ELT and forecasting pipeline, derived live from row counts.
    """
    query = """
    SELECT
        CASE WHEN (SELECT COUNT(*) FROM stg_weather) > 0
             THEN 'Healthy' ELSE 'Missing' END AS weather_status,
        CASE WHEN (SELECT COUNT(*) FROM stg_generation) > 0
             THEN 'Healthy' ELSE 'Missing' END AS generation_status,
        CASE WHEN (SELECT COUNT(*) FROM stg_irradiance) > 0
             THEN 'Healthy' ELSE 'Missing' END AS irradiance_status,
        CASE WHEN (SELECT COUNT(*) FROM stg_daylight) > 0
             THEN 'Healthy' ELSE 'Missing' END AS daylight_status,
        CASE WHEN (SELECT COUNT(*) FROM gold_forecast_features) > 0
             THEN 'Healthy' ELSE 'Missing' END AS feature_status,
        CASE WHEN (SELECT COUNT(*) FROM gold_forecasts) > 0
             THEN 'Healthy' ELSE 'Missing' END AS forecast_status;
    """
    return _run_query(query)