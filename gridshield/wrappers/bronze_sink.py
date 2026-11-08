"""Local-filesystem stand-in for ``src/ingestion/bronze_writer.py``'s S3 upload.

GridShield's storage-isolation requirement means it must never call the
real ``write_bronze()``/``cleanup_old_files()``, which always target the
production ``s3://gridsight-raw`` bucket with no way to redirect them
elsewhere. This module reimplements the same bronze key layout
(``bronze/{source}/{country}/daily/{folder?}/{filename}``) under a
caller-supplied local root instead, so the local tree has the exact same
glob-pattern shape as GridSight's real ``database/queries/daily/*.sql`` —
only the URI scheme/root changes from ``s3://gridsight-raw`` to a local path.

The root is a required, explicit argument (``bronze_root``) rather than a
hardcoded global directory: an audit found that a single shared, unscoped
``bronze_sim/`` directory let one scenario's data silently leak into
another's dbt validation results. ``gridshield.benchmark.runner`` passes a
directory scoped to the specific scenario *and* run attempt currently
executing; ``gridshield.configs.settings.BRONZE_SIM_DIR`` remains available
as a convenience default for standalone/manual use (e.g. in tests), never
for actual benchmark runs.
"""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd

from gridshield.configs.settings import BRONZE_SIM_DIR, DEFAULT_KEEP_DAYS
from src.utils.config import COUNTRY


def _bronze_dir(source: str, folder: Optional[str] = None, bronze_root: Path = BRONZE_SIM_DIR) -> Path:
    """Compute the local directory a bronze CSV for ``source``/``folder`` belongs in.

    Args:
        source: GridSight bronze source path, e.g. ``"weather/openmeteo"``.
        folder: optional grid-point subfolder, e.g. ``"grid_04"``.
        bronze_root: root directory this scenario/run's bronze tree lives under.

    Returns:
        Path: directory mirroring GridSight's S3 key prefix, rooted locally.
    """
    parts = [bronze_root, "bronze", source, COUNTRY, "daily"]
    if folder:
        parts.append(folder)
    return Path(*parts)


def write_bronze_local(
    df: pd.DataFrame,
    source: str,
    filename: str,
    folder: Optional[str] = None,
    bronze_root: Path = BRONZE_SIM_DIR,
) -> Path:
    """Write a DataFrame as CSV into a local bronze_sim tree.

    Mirrors ``write_bronze()``'s key layout and return semantics without
    touching S3.

    Args:
        df: the DataFrame to persist.
        source: GridSight bronze source path, e.g. ``"weather/openmeteo"``.
        filename: CSV filename, e.g. ``"20260725.csv"``.
        folder: optional grid-point subfolder.
        bronze_root: root directory this scenario/run's bronze tree lives under.

    Returns:
        Path: the local file path written.
    """
    directory = _bronze_dir(source, folder, bronze_root)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / filename
    df.to_csv(path, index=False)
    return path


def cleanup_old_files_local(
    source: str,
    folder: Optional[str] = None,
    keep_days: int = DEFAULT_KEEP_DAYS,
    bronze_root: Path = BRONZE_SIM_DIR,
) -> None:
    """Delete bronze_sim CSVs older than ``keep_days``, mirroring ``cleanup_old_files()``'s retention logic.

    Args:
        source: GridSight bronze source path, e.g. ``"weather/openmeteo"``.
        folder: optional grid-point subfolder.
        keep_days: files whose ``YYYYMMDD`` filename stem is older than this
            many days from today (UTC) are deleted.
        bronze_root: root directory this scenario/run's bronze tree lives under.
    """
    directory = _bronze_dir(source, folder, bronze_root)
    if not directory.exists():
        return

    cutoff = datetime.utcnow().date() - timedelta(days=keep_days)

    for csv_file in directory.glob("*.csv"):
        try:
            file_date = datetime.strptime(csv_file.stem, "%Y%m%d").date()
        except ValueError:
            continue
        if file_date < cutoff:
            csv_file.unlink()
