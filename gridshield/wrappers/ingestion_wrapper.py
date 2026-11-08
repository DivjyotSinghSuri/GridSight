"""Wraps GridSight's ingestion fetchers with a reliability strategy and GridShield's local bronze sink.

``src/ingestion/run_ingestion.py::main()`` is hardcoded to "yesterday", the
full 25-point grid, and the real S3 bucket, with no parameters or return
value — it cannot be reused directly for repeatable, fault-injectable
benchmark runs. This module reimplements its per-grid-point orchestration
loop, but calls the exact same atomic, unmodified GridSight functions
(``fetch_weather``, ``fetch_irradiance``, ``fetch_daylight``,
``fetch_generation``) for the actual data retrieval, and writes to
GridShield's isolated local bronze storage (see ``bronze_sink.py``) instead
of GridSight's ``write_bronze``/``cleanup_old_files``.
"""

from dataclasses import dataclass
from datetime import date as date_type
from pathlib import Path
from typing import Callable, List, Optional, Tuple

from src.ingestion.daylight import fetch_daylight
from src.ingestion.generation import fetch_generation
from src.ingestion.irradiance import fetch_irradiance
from src.ingestion.weather import fetch_weather
from src.utils.grid import generate_grid

from gridshield.configs.settings import BRONZE_SIM_DIR
from gridshield.reliability.base import ReliabilityStrategy
from gridshield.wrappers.base import WrapperResult
from gridshield.wrappers.bronze_sink import cleanup_old_files_local, write_bronze_local


@dataclass
class IngestionUnit:
    """One unit of ingestion work: a single fetch-and-store call and its outcome.

    Attributes:
        unit_id: stable checkpoint key identifying this unit of work.
        source_hint: which GridSight data source this unit belongs to
            (``"weather"``, ``"irradiance"``, ``"daylight"``, or
            ``"generation"``).
        result: the :class:`WrapperResult` produced by the reliability
            strategy for this unit of work.
        bronze_source: the GridSight bronze source path this unit was
            written under (e.g. ``"weather/openmeteo"``), so callers (e.g.
            the validation layer) can locate/overwrite its bronze_sim file.
        filename: the CSV filename this unit was written to.
        folder: the optional grid-point subfolder this unit was written under.
    """

    unit_id: str
    source_hint: str
    result: WrapperResult
    bronze_source: str = ""
    filename: str = ""
    folder: Optional[str] = None


def _fetch_and_store(
    fetch_fn: Callable,
    fetch_args: tuple,
    bronze_source: str,
    filename: str,
    folder: Optional[str],
    bronze_root: Path,
) -> Callable[[], object]:
    """Build the zero-argument callable a :class:`ReliabilityStrategy` executes for one unit of work.

    Args:
        fetch_fn: one of GridSight's unmodified ``fetch_*`` functions.
        fetch_args: positional arguments to call ``fetch_fn`` with.
        bronze_source: GridSight bronze source path, e.g. ``"weather/openmeteo"``.
        filename: CSV filename to write, e.g. ``"20260725.csv"``.
        folder: optional grid-point subfolder.
        bronze_root: root directory this scenario/run's bronze tree lives under.

    Returns:
        Callable[[], object]: a zero-argument function that fetches,
        writes to the local bronze sink, prunes old local files, and
        returns the fetched DataFrame.
    """

    def _do():
        df = fetch_fn(*fetch_args)
        write_bronze_local(df, source=bronze_source, filename=filename, folder=folder, bronze_root=bronze_root)
        cleanup_old_files_local(source=bronze_source, folder=folder, bronze_root=bronze_root)
        return df

    return _do


def run_ingestion_scenario(
    strategy: ReliabilityStrategy,
    run_date: date_type,
    grid_points: Optional[List[Tuple[str, float, float]]] = None,
    bronze_root: Path = BRONZE_SIM_DIR,
    stop_after_units: Optional[int] = None,
) -> List[IngestionUnit]:
    """Run one full ingestion pass through GridSight's unmodified fetchers under a reliability strategy.

    Mirrors the per-grid-point loop ``src/ingestion/run_ingestion.py::main()``
    performs (weather + irradiance per grid point, plus one daylight and one
    generation call), but is parameterized by date and grid points and
    routes each fetch-and-store call through ``strategy`` for reliability
    and checkpointing.

    Args:
        strategy: reliability strategy applied to every unit of work.
        run_date: the date to fetch data for.
        grid_points: grid points to iterate; defaults to GridSight's real
            ``generate_grid()`` output (25 points, from ``src/utils/grid.py``).
            Experiments may pass a smaller subset to keep 15-repetition
            benchmark runs tractable — this does not change fetch/fault
            semantics, only how many grid points are sampled per repetition.
        bronze_root: root directory this scenario/run's local bronze tree
            lives under. Must be scoped per scenario (and, for full
            isolation, per run attempt) by the caller — an unscoped shared
            default here previously let one scenario's data leak into
            another's dbt validation results (see
            ``gridshield.benchmark.runner``, which always passes a scoped root).
        stop_after_units: if set, stop after this many units of work have
            been attempted, returning a partial list — simulating a
            process crash partway through ingestion. Used together with a
            checkpoint-aware strategy and a second, uninterrupted call
            (same ``strategy``/checkpoint store) to demonstrate genuine
            interrupt-and-resume behavior: the second call finds the first
            call's completed units already checkpointed and skips
            re-fetching them. ``None`` (the default) runs the full pass
            with no simulated interruption.

    Returns:
        list[IngestionUnit]: one entry per fetch-and-store call attempted,
        in execution order. Has fewer than the full expected count if
        ``stop_after_units`` cut it short.
    """
    grid_points = grid_points if grid_points is not None else generate_grid()
    filename = f"{run_date:%Y%m%d}.csv"
    units: List[IngestionUnit] = []

    def _reached_stop_point() -> bool:
        return stop_after_units is not None and len(units) >= stop_after_units

    for grid_id, lat, lon in grid_points:
        if _reached_stop_point():
            return units

        weather_key = f"weather:{grid_id}:{run_date:%Y-%m-%d}"
        weather_result = strategy.execute(
            _fetch_and_store(
                fetch_weather, (lat, lon, run_date, run_date), "weather/openmeteo", filename, grid_id, bronze_root
            ),
            checkpoint_key=weather_key,
        )
        units.append(IngestionUnit(weather_key, "weather", weather_result, "weather/openmeteo", filename, grid_id))

        if _reached_stop_point():
            return units

        irradiance_key = f"irradiance:{grid_id}:{run_date:%Y-%m-%d}"
        irradiance_result = strategy.execute(
            _fetch_and_store(
                fetch_irradiance,
                (lat, lon, run_date, run_date),
                "irradiance/openmeteo",
                filename,
                grid_id,
                bronze_root,
            ),
            checkpoint_key=irradiance_key,
        )
        units.append(
            IngestionUnit(irradiance_key, "irradiance", irradiance_result, "irradiance/openmeteo", filename, grid_id)
        )

    if _reached_stop_point():
        return units

    daylight_key = f"daylight:{run_date:%Y-%m-%d}"
    daylight_result = strategy.execute(
        _fetch_and_store(fetch_daylight, (run_date, run_date), "daylight/openmeteo", filename, None, bronze_root),
        checkpoint_key=daylight_key,
    )
    units.append(IngestionUnit(daylight_key, "daylight", daylight_result, "daylight/openmeteo", filename, None))

    if _reached_stop_point():
        return units

    generation_key = f"generation:{run_date:%Y-%m-%d}"
    generation_result = strategy.execute(
        _fetch_and_store(fetch_generation, (run_date, run_date), "generation/entsoe", filename, None, bronze_root),
        checkpoint_key=generation_key,
    )
    units.append(IngestionUnit(generation_key, "generation", generation_result, "generation/entsoe", filename, None))

    return units
