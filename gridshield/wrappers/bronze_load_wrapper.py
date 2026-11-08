"""Loads GridShield's local bronze_sim CSVs into GridShield's isolated DuckDB.

Mirrors ``database/load_bronze_daily.py::load_bronze()``, which is
hardcoded to ``config.DATABASE_PATH`` and executes
``database/queries/daily/*.sql`` — SQL files that hardcode
``s3://gridsight-raw/...`` globs. Because GridShield's storage-isolation
requirement means bronze data lives locally under
``gridshield/outputs/bronze_sim/`` rather than S3, those exact ``.sql``
files cannot be executed as-is; this module reimplements the same
``CREATE OR REPLACE TABLE bronze_x AS SELECT * FROM read_csv_auto(...)``
pattern, glob-for-glob, against the local bronze_sim tree and GridShield's
own isolated DuckDB file instead of GridSight's production database.
"""

import glob as glob_module
from pathlib import Path

import duckdb

from gridshield.configs.settings import BRONZE_SIM_DIR, GRIDSHIELD_DB_PATH

_BRONZE_TABLES = {
    "bronze_weather": "weather/openmeteo/germany/daily/*/*.csv",
    "bronze_irradiance": "irradiance/openmeteo/germany/daily/*/*.csv",
    "bronze_daylight": "daylight/openmeteo/germany/daily/*.csv",
    "bronze_generation": "generation/entsoe/germany/daily/*.csv",
}
"""Maps each bronze table name to the glob (relative to bronze_sim/bronze/) of its source CSVs.

Mirrors the four ``database/queries/daily/bronze_*.sql`` files' table
names and glob shapes exactly.
"""


def load_bronze_local(
    db_path: Path = GRIDSHIELD_DB_PATH, bronze_dir: Path = BRONZE_SIM_DIR
) -> dict:
    """Load GridShield's local bronze_sim CSVs into the isolated DuckDB file, one table per source.

    Args:
        db_path: path to GridShield's isolated DuckDB file.
        bronze_dir: root of the local bronze_sim tree written by ``bronze_sink.py``.

    Returns:
        dict[str, int]: row count loaded per bronze table. A table is
        skipped (left absent) if no matching CSVs exist yet.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    row_counts: dict = {}

    with duckdb.connect(str(db_path)) as conn:
        for table_name, glob_suffix in _BRONZE_TABLES.items():
            glob_path = bronze_dir / "bronze" / glob_suffix

            if not glob_module.glob(str(glob_path)):
                continue

            conn.execute(
                f"CREATE OR REPLACE TABLE {table_name} AS "
                f"SELECT * FROM read_csv_auto('{glob_path.as_posix()}');"
            )
            row_counts[table_name] = conn.execute(
                f"SELECT COUNT(*) FROM {table_name};"
            ).fetchone()[0]

    return row_counts