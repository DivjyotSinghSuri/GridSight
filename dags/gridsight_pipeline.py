import os
import sys
from pathlib import Path
from datetime import datetime, timedelta

PROJECT_ROOT = None

if os.environ.get("GRIDSIGHT_PROJECT_ROOT"):
    PROJECT_ROOT = Path(os.environ["GRIDSIGHT_PROJECT_ROOT"]).expanduser().resolve()

if PROJECT_ROOT is None:
    candidate_paths = [
        Path(__file__).resolve().parent,
        Path.cwd().resolve(),
    ]
    for start_path in candidate_paths:
        for candidate in [start_path] + list(start_path.parents):
            if (candidate / "config.py").is_file() and (candidate / "src").is_dir():
                PROJECT_ROOT = candidate
                break
        if PROJECT_ROOT is not None:
            break

if PROJECT_ROOT is None:
    raise RuntimeError(
        "Could not locate the GridSight project root. "
        "Set GRIDSIGHT_PROJECT_ROOT to the repository root."
    )

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import DATABASE_PATH
from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator
from airflow.providers.standard.operators.bash import BashOperator

from src.ingestion.run_ingestion import main as run_ingestion
from database.load_bronze_daily import load_bronze
from src.forecasting.run_forecast import run_forecast


default_args = {
    "owner": "divjyot",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}


def validate_forecasts():
    import duckdb

    with duckdb.connect(str(DATABASE_PATH)) as con:

        row_count = con.execute("""
            SELECT COUNT(*)
            FROM gold_forecasts
        """).fetchone()[0]

        latest = con.execute("""
            SELECT MAX(forecast_created_at)
            FROM gold_forecasts
        """).fetchone()[0]

    if row_count == 0:
        raise ValueError("gold_forecasts is empty.")

    print(f"Forecast rows: {row_count}")
    print(f"Latest forecast run: {latest}")


with DAG(
    dag_id="gridsight_pipeline",
    description="Daily GridSight ELT + Forecast Pipeline",
    default_args=default_args,
    start_date=datetime(2026, 7, 20),
    schedule="0 2 * * *",
    catchup=False,
    tags=["gridsight", "forecasting", "duckdb", "dbt"],
) as dag:

    ingestion_task = PythonOperator(
        task_id="daily_ingestion",
        python_callable=run_ingestion,
    )

    bronze_task = PythonOperator(
        task_id="load_bronze",
        python_callable=load_bronze,
    )

    dbt_task = BashOperator(
        task_id="dbt_run",
        bash_command=f"""
        cd {PROJECT_ROOT}/gridsight_dbt &&
        dbt deps &&
        dbt run --select +gold_forecast_features
        """,
    )

    forecast_task = PythonOperator(
        task_id="run_forecast",
        python_callable=run_forecast,
    )

    validation_task = PythonOperator(
        task_id="validate_forecasts",
        python_callable=validate_forecasts,
    )

    ingestion_task >> bronze_task >> dbt_task >> forecast_task >> validation_task
