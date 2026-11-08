"""GridShield's benchmark engine: runs a Scenario for its configured repetitions.

Every scenario run lives in its own timestamped, config-fingerprinted
directory under ``gridshield/outputs/<experiment_id>/<scenario_id>/runs/``:
``<UTC timestamp>_<config fingerprint prefix>/``. This gives every attempt
— successful, crashed, or superseded by an edited config — a permanent,
never-overwritten record with its own ``config.json``/``metadata.json``,
satisfying two requirements together:

* **Restartable.** If the process crashes midway, re-running the same
  scenario with an *unchanged* config resumes the same run directory,
  skipping repetitions already recorded in its ``progress.json``.
* **Config-drift safe.** If the scenario's YAML is edited before
  re-running (even with the same ``scenario_id``), the new config's
  fingerprint won't match any existing *incomplete* run directory, so a
  fresh run directory is created instead of silently reusing or mixing in
  stale results from a different configuration.

``<scenario_dir>/latest.json`` always points at the most recently
touched run directory, for tools (like the plotting module) that just
want "the" current result per scenario. Nothing is ever deleted or
overwritten in place — every run directory, once created, is permanent.
"""

import hashlib
import json
import shutil
import time
from datetime import date as date_type
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Set, Tuple

import pandas as pd

from gridshield.benchmark.metadata import collect_run_metadata
from gridshield.benchmark.scenario import Scenario
from gridshield.configs.logging_setup import get_scenario_logger
from gridshield.configs.seeding import derive_run_seed, seed_all
from gridshield.configs.settings import EXPERIMENTS_OUTPUT_DIR
from gridshield.fault_injection.faults import Fault
from gridshield.fault_injection.injector import FaultInjector
from gridshield.metrics.overhead_metrics import measure_directory_size, track_peak_memory
from gridshield.metrics.reliability_metrics import compute_reliability_metrics
from gridshield.metrics.validation_metrics import compute_validation_metrics
from gridshield.reliability.base import ReliabilityStrategy
from gridshield.reliability.baseline import BaselineStrategy
from gridshield.reliability.checkpoint_store import CheckpointStore
from gridshield.reliability.checkpointing import CheckpointedBackoffStrategy
from gridshield.reliability.exponential_backoff import ExponentialBackoffStrategy
from gridshield.reliability.fixed_retry import FixedRetryStrategy
from gridshield.statistics.aggregator import aggregate_statistics
from gridshield.validation.base import ValidationReport
from gridshield.validation.corruption import corrupt_dataframe
from gridshield.validation.python_validation.checks import build_default_checks
from gridshield.validation.python_validation.validator import PythonValidator
from gridshield.wrappers.bronze_load_wrapper import load_bronze_local
from gridshield.wrappers.bronze_sink import write_bronze_local
from gridshield.wrappers.dbt_wrapper import DbtValidationWrapper
from gridshield.wrappers.ingestion_wrapper import run_ingestion_scenario
from src.utils.grid import generate_grid

RELIABILITY_METRIC_COLUMNS = [
    "recovery_rate", "recovery_time_seconds", "runtime_seconds", "api_calls", "data_completeness",
]
"""results.csv columns produced by the Reliability Layer, aggregated by statistics/aggregator.py."""

VALIDATION_METRIC_COLUMNS = ["detection_rate", "false_positive_rate", "propagation"]
"""results.csv columns produced by the Validation Layer."""

OVERHEAD_METRIC_COLUMNS = ["storage_bytes", "peak_memory_bytes"]
"""results.csv columns produced by the overhead measurement (runtime is shared with reliability)."""

ALL_METRIC_COLUMNS = RELIABILITY_METRIC_COLUMNS + VALIDATION_METRIC_COLUMNS + OVERHEAD_METRIC_COLUMNS


def _fingerprint(config: dict) -> str:
    """Compute a stable content hash of a scenario config dict.

    Args:
        config: a JSON-serializable dict, e.g. ``Scenario.as_dict()``.

    Returns:
        str: hex-encoded SHA-256 digest of the config's canonical
        (sorted-key) JSON serialization.
    """
    canonical = json.dumps(config, sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _build_reliability_strategy(
    scenario: Scenario, checkpoint_store: CheckpointStore
) -> ReliabilityStrategy:
    """Construct the reliability strategy named by ``scenario.reliability_strategy``.

    Args:
        scenario: the scenario whose ``reliability_strategy``/``reliability_params`` to use.
        checkpoint_store: the store passed to :class:`CheckpointedBackoffStrategy`; ignored by other strategies.

    Returns:
        ReliabilityStrategy: a configured, ready-to-use strategy instance.

    Raises:
        ValueError: if ``scenario.reliability_strategy`` is not recognized.
    """
    name = scenario.reliability_strategy
    params = scenario.reliability_params
    if name == "baseline":
        return BaselineStrategy()
    if name == "fixed_retry":
        return FixedRetryStrategy(**params)
    if name == "exponential_backoff":
        return ExponentialBackoffStrategy(**params)
    if name == "checkpointing":
        return CheckpointedBackoffStrategy(checkpoint_store=checkpoint_store, **params)
    raise ValueError(f"Unknown reliability_strategy: {name}")


class BenchmarkRunner:
    """Runs one :class:`Scenario` for its configured number of repetitions.

    Every run lives in its own permanent, timestamped, config-fingerprinted
    directory (see module docstring). Storage (local bronze CSVs, the
    isolated DuckDB file, checkpoint state) is scoped to that one run
    directory, so it can never leak into or be contaminated by another
    scenario's or another run's data.
    """

    def __init__(self, scenario: Scenario, output_root: Path = EXPERIMENTS_OUTPUT_DIR):
        """Configure a runner for one scenario, resolving which run directory to use.

        Args:
            scenario: the scenario to run.
            output_root: base directory under which
                ``<experiment_id>/<scenario_id>/runs/<run_id>/`` artifacts are written.
        """
        self.scenario = scenario
        self.scenario_dir = output_root / scenario.experiment_id / scenario.scenario_id
        self.runs_dir = self.scenario_dir / "runs"
        self.runs_dir.mkdir(parents=True, exist_ok=True)

        self.config_fingerprint = _fingerprint(scenario.as_dict())
        self.run_id, self.is_resuming = self._resolve_run_id()

        self.run_dir = self.runs_dir / self.run_id
        self.run_dir.mkdir(parents=True, exist_ok=True)

        self.logs_dir = self.run_dir / "logs"
        self.bronze_root = self.run_dir / "bronze_sim"
        self.db_path = self.run_dir / "gridshield.duckdb"
        self.checkpoints_dir = self.run_dir / "checkpoints"
        self.logger = get_scenario_logger(f"{scenario.scenario_id}__{self.run_id}", self.logs_dir)
        self.results_path = self.run_dir / "results.csv"
        self.progress_path = self.run_dir / "progress.json"

    def _resolve_run_id(self) -> Tuple[str, bool]:
        """Find an existing, incomplete run directory with a matching config to resume, else mint a fresh one.

        Returns:
            tuple[str, bool]: ``(run_id, is_resuming)``.
        """
        if self.runs_dir.exists():
            for candidate in sorted(self.runs_dir.iterdir()):
                if not candidate.is_dir():
                    continue
                config_path = candidate / "config.json"
                if not config_path.exists():
                    continue
                with open(config_path) as f:
                    existing_config = json.load(f)
                if _fingerprint(existing_config) != self.config_fingerprint:
                    continue

                completed: Set[int] = set()
                progress_path = candidate / "progress.json"
                if progress_path.exists():
                    with open(progress_path) as f:
                        completed = set(json.load(f).get("completed_repetitions", []))

                if len(completed) < self.scenario.repetitions:
                    return candidate.name, True

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        return f"{timestamp}_{self.config_fingerprint[:8]}", False

    def _load_progress(self) -> Set[int]:
        """Load the set of already-completed repetition numbers from ``progress.json``."""
        if self.progress_path.exists():
            with open(self.progress_path) as f:
                return set(json.load(f).get("completed_repetitions", []))
        return set()

    def _save_progress(self, completed: Set[int]) -> None:
        """Persist the set of completed repetition numbers to ``progress.json``."""
        with open(self.progress_path, "w") as f:
            json.dump({"completed_repetitions": sorted(completed)}, f, indent=2)

    def _append_result_row(self, row: dict) -> None:
        """Append one repetition's result row to ``results.csv``, writing a header only if the file is new."""
        row_df = pd.DataFrame([row])
        write_header = not self.results_path.exists()
        row_df.to_csv(self.results_path, mode="a", header=write_header, index=False)

    def _update_latest_pointer(self) -> None:
        """Point ``<scenario_dir>/latest.json`` at this runner's run directory."""
        with open(self.scenario_dir / "latest.json", "w") as f:
            json.dump({"run_id": self.run_id}, f, indent=2)

    def run(self) -> pd.DataFrame:
        """Run every repetition of this scenario not already recorded as complete in this run directory.

        Writes (or refreshes) ``config.json`` and writes ``metadata.json``
        once per run directory, appends one row to ``results.csv`` per
        repetition as it completes, updates ``progress.json`` after each
        repetition so a crash loses at most one repetition's work, writes
        ``summary.csv``/``statistics.csv`` from the accumulated results,
        and updates the scenario's ``latest.json`` pointer.

        Returns:
            pd.DataFrame: this run directory's full ``results.csv``
            contents after this call, including repetitions completed in
            prior, interrupted invocations of the same run.
        """
        scenario = self.scenario
        completed = self._load_progress()
        self.logger.info(
            f"{'Resuming' if self.is_resuming else 'Starting'} run {self.run_id} "
            f"for scenario {scenario.scenario_id}: "
            f"{len(completed)}/{scenario.repetitions} repetitions already complete."
        )

        with open(self.run_dir / "config.json", "w") as f:
            json.dump(scenario.as_dict(), f, indent=2)

        metadata_path = self.run_dir / "metadata.json"
        if not metadata_path.exists():
            with open(metadata_path, "w") as f:
                json.dump(collect_run_metadata(scenario), f, indent=2, default=str)

        grid_points = generate_grid()
        if scenario.grid_points_limit:
            grid_points = grid_points[: scenario.grid_points_limit]
        run_date = date_type.fromisoformat(scenario.run_date)

        for run_number in range(scenario.repetitions):
            if run_number in completed:
                continue

            self.logger.info(f"Repetition {run_number + 1}/{scenario.repetitions} starting.")
            row = self._run_one_repetition(run_number, grid_points, run_date)
            self._append_result_row(row)

            completed.add(run_number)
            self._save_progress(completed)
            self.logger.info(f"Repetition {run_number + 1}/{scenario.repetitions} complete: {row}")

        self._write_summary_and_statistics()
        self._update_latest_pointer()
        return pd.read_csv(self.results_path) if self.results_path.exists() else pd.DataFrame()

    def _run_one_repetition(self, run_number: int, grid_points, run_date: date_type) -> dict:
        """Run a single repetition: ingestion under fault injection, then validation, then metrics.

        If ``scenario.simulate_interruption_after_units`` is set, ingestion
        runs in two passes sharing the same reliability strategy and
        checkpoint store: a first pass that stops early (simulating a
        process crash), then a second, full pass. This is the only way a
        checkpointing strategy's actual value — resuming without redoing
        completed work — can be observed; without it, a checkpoint store
        constructed fresh at the start of every repetition never has any
        prior state to resume from, and "checkpointing" is indistinguishable
        from "exponential_backoff" in the collected metrics.

        ``runtime_seconds``/``peak_memory_bytes`` cover ingestion *and*
        validation (Python checks and, for ``dbt``/``combined``, the ``dbt``
        subprocess) — both run inside the same timed, memory-tracked block
        — so they reflect the full per-repetition cost Experiments 3/4
        compare between the baseline and full-GridShield arms. For
        scenarios with ``validation_strategy: "none"`` (all of Experiment 1)
        this is identical to timing ingestion alone.

        Args:
            run_number: zero-based repetition index.
            grid_points: grid points to sample for this repetition.
            run_date: the ingestion date to fetch.

        Returns:
            dict: one row for ``results.csv``.
        """
        scenario = self.scenario
        run_seed = derive_run_seed(scenario.master_seed, scenario.scenario_id, run_number)
        seed_all(run_seed)

        fault_type = (
            Fault(scenario.fault_type)
            if scenario.fault_type and scenario.fault_type != "none"
            else None
        )
        checkpoint_store = CheckpointStore(f"run{run_number}", checkpoints_dir=self.checkpoints_dir)
        strategy = _build_reliability_strategy(scenario, checkpoint_store)

        start = time.monotonic()
        with track_peak_memory() as mem, FaultInjector(
            fault_type,
            scenario.fault_probability,
            run_seed,
            scenario_id=scenario.scenario_id,
            run_number=run_number,
        ) as injector:
            if scenario.simulate_interruption_after_units is not None:
                interrupted_units = run_ingestion_scenario(
                    strategy,
                    run_date,
                    grid_points=grid_points,
                    bronze_root=self.bronze_root,
                    stop_after_units=scenario.simulate_interruption_after_units,
                )
                self.logger.info(
                    f"Simulated interruption after {len(interrupted_units)} unit(s) "
                    f"(requested stop_after_units={scenario.simulate_interruption_after_units}); "
                    "starting the resumed pass."
                )
            units = run_ingestion_scenario(
                strategy, run_date, grid_points=grid_points, bronze_root=self.bronze_root
            )
            validation_metrics, validation_status, validation_error = self._run_validation_safely(
                units, run_seed, run_number
            )
        runtime_seconds = time.monotonic() - start

        injector.log.write_json(self.logs_dir / f"fault_log_run{run_number}.json")

        reliability_metrics = compute_reliability_metrics(units, injector.log, runtime_seconds)

        storage_bytes = measure_directory_size(self.bronze_root)
        if self.db_path.exists():
            storage_bytes += self.db_path.stat().st_size

        return {
            "scenario_id": scenario.scenario_id,
            "run_id": self.run_id,
            "run_number": run_number,
            "seed": run_seed,
            "fault_type": scenario.fault_type,
            "fault_probability": scenario.fault_probability,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "recovery_rate": reliability_metrics.recovery_rate,
            "recovery_time_seconds": reliability_metrics.recovery_time_seconds,
            "runtime_seconds": reliability_metrics.runtime_seconds,
            "api_calls": reliability_metrics.api_calls,
            "data_completeness": reliability_metrics.data_completeness,
            "detection_rate": validation_metrics.detection_rate if validation_metrics else None,
            "false_positive_rate": (
                validation_metrics.false_positive_rate if validation_metrics else None
            ),
            "propagation": validation_metrics.propagation if validation_metrics else None,
            "validation_status": validation_status,
            "validation_error": validation_error,
            "storage_bytes": storage_bytes,
            "peak_memory_bytes": mem.get("peak_bytes"),
        }

    def _run_validation_safely(self, units, run_seed: int, run_number: int):
        """Run ``_run_validation()``, converting a dbt model-build failure into an honest result row.

        ``schema_mismatch`` and ``missing_rows`` are severe enough (an
        entire column dropped; every row emptied) that GridShield's
        staging dbt models can fail to build at all — before ``dbt test``
        ever runs — for ``dbt``/``combined`` validation strategies. That is
        a genuine, disclosable finding (dbt's static-SQL transform layer
        cannot survive these two violation types, unlike Python validation,
        which runs directly against the DataFrame), not a value to paper
        over with a fabricated ``detection_rate``. Rather than letting the
        exception abort the whole repetition (and, without per-scenario
        isolation upstream, potentially the whole benchmark run), this
        records the failure explicitly via ``validation_status``/
        ``validation_error`` and leaves ``detection_rate``/
        ``false_positive_rate``/``propagation`` as ``None`` (not zero, not
        one) — "not measurable", not "measured as bad".

        Args:
            units: outcomes of every ingestion unit of work attempted.
            run_seed: this repetition's derived seed.
            run_number: zero-based repetition index.

        Returns:
            tuple[ValidationMetrics | None, str, str | None]:
            ``(metrics, status, error)``. ``status`` is ``"none"`` when
            ``validation_strategy`` is ``"none"``, ``"ok"`` on a normal
            run, or ``"dbt_run_failed"`` if ``dbt run`` failed to build the
            staging models; ``error`` carries the exception message in
            that last case, else ``None``.
        """
        try:
            validation_metrics = self._run_validation(units, run_seed, run_number)
        except RuntimeError as exc:
            self.logger.error(f"Validation failed for repetition {run_number}: {exc}")
            return None, "dbt_run_failed", str(exc)
        status = "none" if validation_metrics is None else "ok"
        return validation_metrics, status, None

    def _run_validation(self, units, run_seed: int, run_number: int):
        """Run the configured validation strategy against this repetition's fetched data.

        Deterministically injects at most one data-quality violation (per
        ``scenario.validation_params["inject_violation"]``) into a copy of
        each successful unit's DataFrame, establishing ground truth. Python
        checks (if configured) run against that corrupted copy directly;
        dbt checks (if configured) run against the same corrupted copy
        after it is written into this run's own local bronze_sim tree and
        loaded into this run's own isolated DuckDB file — so "combined"
        validation gives both engines an identical view of the data, and
        neither engine can see another scenario's or run's data.

        Args:
            units: outcomes of every ingestion unit of work attempted.
            run_seed: this repetition's derived seed, used to pick which
                row(s) get corrupted.
            run_number: zero-based repetition index, used to name the
                archived dbt result artifacts for this repetition.

        Returns:
            ValidationMetrics | None: ``None`` if ``validation_strategy`` is ``"none"``.
        """
        scenario = self.scenario
        if scenario.validation_strategy == "none":
            return None

        violation_type = scenario.validation_params.get("inject_violation", "none")
        needs_python = scenario.validation_strategy in ("python", "combined")
        needs_dbt = scenario.validation_strategy in ("dbt", "combined")

        injected_check_names: Set[str] = set()
        results = []

        for unit in units:
            if not unit.result.success or unit.result.value is None:
                continue

            corrupted_df, expected_check = corrupt_dataframe(
                unit.result.value, unit.source_hint, violation_type, run_seed
            )
            if expected_check:
                injected_check_names.add(expected_check)

            if needs_python:
                report = PythonValidator(build_default_checks(unit.source_hint)).validate(corrupted_df)
                results.extend(report.results)

            if needs_dbt:
                write_bronze_local(
                    corrupted_df,
                    source=unit.bronze_source,
                    filename=unit.filename,
                    folder=unit.folder,
                    bronze_root=self.bronze_root,
                )

        if needs_dbt:
            load_bronze_local(db_path=self.db_path, bronze_dir=self.bronze_root)
            dbt_wrapper = DbtValidationWrapper(db_path=self.db_path)
            dbt_wrapper.run_models()
            results.extend(dbt_wrapper.run_tests())
            self._archive_dbt_artifacts(dbt_wrapper, run_number)

        report = ValidationReport(results=results)
        return compute_validation_metrics(report, injected_check_names)

    def _archive_dbt_artifacts(self, dbt_wrapper: DbtValidationWrapper, run_number: int) -> None:
        """Copy this repetition's dbt run_results.json/manifest.json into this run's logs/ for the audit trail.

        dbt's ``target/`` directory belongs to the shared standalone dbt
        project and gets overwritten by the next invocation (the next
        repetition, or another scenario entirely) — copying these two
        files out preserves exactly which dbt tests ran and how they
        resolved for this specific repetition.

        Args:
            dbt_wrapper: the wrapper whose most recent ``dbt test``
                invocation's artifacts should be archived.
            run_number: zero-based repetition index, used in the archived filenames.
        """
        target_dir = dbt_wrapper.project_dir / "target"
        for artifact_name in ("run_results.json", "manifest.json"):
            source_path = target_dir / artifact_name
            if source_path.exists():
                shutil.copyfile(
                    source_path, self.logs_dir / f"dbt_{artifact_name.replace('.json', '')}_run{run_number}.json"
                )

    def _write_summary_and_statistics(self) -> None:
        """Write ``summary.csv`` (per-metric point estimates) and ``statistics.csv`` (mean/std/95% CI)."""
        if not self.results_path.exists():
            return
        results_df = pd.read_csv(self.results_path)
        stats_df = aggregate_statistics(results_df, ALL_METRIC_COLUMNS)
        stats_df.to_csv(self.run_dir / "statistics.csv", index=False)

        summary_df = stats_df[["metric", "mean"]] if not stats_df.empty else stats_df
        summary_df.to_csv(self.run_dir / "summary.csv", index=False)
