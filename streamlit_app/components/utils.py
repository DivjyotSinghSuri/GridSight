"""
Shared, read-only data-access helpers for the GridSight dashboard.

IMPORTANT: DuckDB is single-writer. The Airflow DAG (gridsight_daily_dag.py)
writes to this same database file every day. This dashboard must never
hold a persistent read-write connection open, or it risks locking the
file and blocking the pipeline's write step. Every helper below opens a
short-lived, read_only=True connection and closes it immediately.
"""
import json
from datetime import datetime, timezone

import duckdb
import pandas as pd
import streamlit as st

from ..config import (
    DATABASE_PATH,
    FORECAST_TABLE,
    GENERATION_VIEW,
    WEATHER_VIEW,
    DAYLIGHT_VIEW,
    METRICS_PATH,
    FALLBACK_METRICS,
)


def _connect() -> duckdb.DuckDBPyConnection:
    return duckdb.connect(DATABASE_PATH, read_only=True)


@st.cache_data(ttl=300)
def run_query(sql: str) -> pd.DataFrame:
    """Runs a read-only SQL query against the DuckDB warehouse."""
    con = _connect()
    try:
        return con.execute(sql).df()
    finally:
        con.close()


@st.cache_data(ttl=300)
def load_latest_forecast_window(hours: int = 24) -> pd.DataFrame:
    sql = f"""
        SELECT *
        FROM {FORECAST_TABLE}
        WHERE forecast_timestamp > (
            SELECT MAX(forecast_timestamp) - INTERVAL '{hours} hours'
            FROM {FORECAST_TABLE}
        )
        ORDER BY forecast_timestamp
    """

    try:
        df = run_query(sql)

        if not df.empty:
            df = df.rename(
                columns={
                    "forecast_timestamp": "timestamp"
                }
            )

            df["timestamp"] = pd.to_datetime(df["timestamp"])

        return df

    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=300)
def load_historical_generation(days: int = 30) -> pd.DataFrame:
    sql = f"""
        SELECT timestamp, solar_generation_mw
        FROM {GENERATION_VIEW}
        WHERE timestamp > (
            SELECT MAX(timestamp) - INTERVAL '{days} days' FROM {GENERATION_VIEW}
        )
        ORDER BY timestamp
    """
    try:
        df = run_query(sql)
        if not df.empty:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
        return df
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def load_latest_weather() -> pd.Series:
    sql = f"""
        SELECT * FROM {WEATHER_VIEW}
        ORDER BY timestamp DESC
        LIMIT 1
    """
    try:
        df = run_query(sql)
        return df.iloc[0] if not df.empty else pd.Series(dtype="float64")
    except Exception:
        return pd.Series(dtype="float64")


@st.cache_data(ttl=300)
def load_latest_daylight() -> pd.Series:
    sql = f"""
        SELECT * FROM {DAYLIGHT_VIEW}
        ORDER BY date DESC
        LIMIT 1
    """
    try:
        df = run_query(sql)
        return df.iloc[0] if not df.empty else pd.Series(dtype="object")
    except Exception:
        return pd.Series(dtype="object")


def load_metrics() -> dict:
    """Loads saved evaluation metrics, falling back to static config values."""
    if METRICS_PATH.exists():
        with open(METRICS_PATH) as f:
            return json.load(f)
    return FALLBACK_METRICS


def last_pipeline_run_utc() -> str:
    """
    Reads the most recent forecast_created_at from gold_forecasts as a
    proxy for 'last pipeline run'. Returns a readable fallback if the
    table is empty, missing, or the database is unreachable -- this must
    never raise, since it renders in the sidebar on every page.
    """
    try:
        df = run_query(f"SELECT MAX(forecast_created_at) AS last_run FROM {FORECAST_TABLE}")
        if df.empty or pd.isna(df.iloc[0]["last_run"]):
            return "No runs yet"
        return str(df.iloc[0]["last_run"])
    except Exception:
        return "Unavailable"


def database_is_reachable() -> bool:
    try:
        run_query("SELECT 1")
        return True
    except Exception:
        return False


def today_utc():
    return datetime.now(timezone.utc).date()