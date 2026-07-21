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
    return duckdb.connect(str(DATABASE_PATH), read_only=True)


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
        df = run_query(
            f"SELECT MAX(forecast_created_at) AS last_run FROM {FORECAST_TABLE}")
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


def _format_number(value, decimals: int = 0, comma: bool = True) -> str:
    try:
        value = float(value)
    except (TypeError, ValueError):
        return "—"

    fmt = f"{{:,.{decimals}f}}" if comma else f"{{:.{decimals}f}}"
    return fmt.format(value)


def format_power(value, unit: str = "MW") -> str:
    if value is None or pd.isna(value):
        return "—"

    try:
        value = float(value)
    except (TypeError, ValueError):
        return str(value)

    decimals = 0 if abs(value) >= 100 else 1
    return f"{_format_number(value, decimals)} {unit}"


def format_energy(value, unit: str = "MWh") -> str:
    if value is None or pd.isna(value):
        return "—"
    try:
        return f"{_format_number(value, 0)} {unit}"
    except (TypeError, ValueError):
        return str(value)


def format_temperature(value) -> str:
    if value is None or pd.isna(value):
        return "—"
    try:
        return f"{float(value):.1f} °C"
    except (TypeError, ValueError):
        return str(value)


def format_percentage(value, decimals: int = 2) -> str:
    if value is None or pd.isna(value):
        return "—"
    try:
        return f"{float(value):.{decimals}f}%"
    except (TypeError, ValueError):
        return str(value)


def format_humidity(value) -> str:
    if value is None or pd.isna(value):
        return "—"
    try:
        return f"{float(value):.1f} %"
    except (TypeError, ValueError):
        return str(value)


def format_wind_speed(value) -> str:
    if value is None or pd.isna(value):
        return "—"
    try:
        return f"{float(value):.1f} km/h"
    except (TypeError, ValueError):
        return str(value)


def format_cloud_cover(value) -> str:
    if value is None or pd.isna(value):
        return "—"
    try:
        return f"{int(round(float(value)))}%"
    except (TypeError, ValueError):
        return str(value)


def format_precipitation(value) -> str:
    if value is None or pd.isna(value):
        return "—"
    try:
        return f"{float(value):.2f} mm"
    except (TypeError, ValueError):
        return str(value)


def format_timestamp(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "—"
    if isinstance(value, (pd.Timestamp, datetime)):
        try:
            return value.strftime("%Y-%m-%d %H:%M")
        except Exception:
            return str(value)
    try:
        return str(value)
    except Exception:
        return "—"
