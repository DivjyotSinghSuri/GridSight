"""Reliability-layer metrics: recovery rate, recovery time, runtime, API calls, data completeness."""

from dataclasses import dataclass
from typing import List

from gridshield.fault_injection.experiment_log import ExperimentLog
from gridshield.fault_injection.fixture_shapes import EXPECTED_ROWS_PER_SOURCE
from gridshield.wrappers.ingestion_wrapper import IngestionUnit


def _row_count(unit: IngestionUnit) -> int:
    """Row count a successful unit contributes to Data Completeness.

    Units resumed from a checkpoint (``resumed_from_checkpoint=True``)
    have no ``.value`` — the whole point of skipping them is not
    re-fetching the DataFrame — but they were only ever marked complete
    after a genuinely successful fetch in an earlier pass, so they are
    credited with their source's full expected row count rather than 0
    (which would understate completeness for the checkpointing strategy
    specifically, undermining the metric it most needs to be fair to).

    Args:
        unit: a successful ingestion unit.

    Returns:
        int: rows to credit toward Data Completeness for this unit.
    """
    if unit.result.value is not None:
        return len(unit.result.value)
    if unit.result.resumed_from_checkpoint:
        return EXPECTED_ROWS_PER_SOURCE.get(unit.source_hint, 0)
    return 0


@dataclass
class ReliabilityMetrics:
    """Aggregate reliability metrics for one scenario repetition.

    Attributes:
        recovery_rate: fraction of ingestion units that ultimately succeeded,
            out of all units attempted. Unit-weighted: every unit of work
            (one fetch-and-store call) counts equally regardless of source.
        recovery_time_seconds: mean ``duration_seconds`` of units that needed
            more than one attempt to succeed (0.0 if none did).
        runtime_seconds: total wall-clock time for the repetition.
        api_calls: total number of ``requests.get`` calls observed (real or
            simulated) during the repetition.
        data_completeness: fraction of the total *expected data volume*
            (rows, summed across all attempted units) actually captured by
            successful units. Row-weighted: a failure in a
            higher-row-count source (e.g. weather, 6 rows/unit) reduces
            completeness more than a failure in a lower-row-count source
            (e.g. daylight, 1 row/unit) — distinct from recovery_rate,
            which weights every unit equally regardless of source. The two
            are equal only when failures are evenly distributed across
            sources with equal row counts.
        total_units: number of ingestion units attempted.
        successful_units: number of ingestion units that ultimately succeeded.
    """

    recovery_rate: float
    recovery_time_seconds: float
    runtime_seconds: float
    api_calls: int
    data_completeness: float
    total_units: int
    successful_units: int


def compute_reliability_metrics(
    units: List[IngestionUnit],
    fault_log: ExperimentLog,
    runtime_seconds: float,
) -> ReliabilityMetrics:
    """Compute aggregate reliability metrics for one scenario repetition.

    Args:
        units: outcomes of every ingestion unit of work attempted, as
            returned by ``ingestion_wrapper.run_ingestion_scenario()``.
        fault_log: the FaultInjector's call-level log for the same repetition.
        runtime_seconds: measured wall-clock duration of the whole repetition.

    Returns:
        ReliabilityMetrics: the five metrics Experiment 1 compares across
        reliability strategies.
    """
    total_units = len(units)
    successful = [u for u in units if u.result.success]
    successful_units = len(successful)

    recovered = [u for u in successful if u.result.attempts > 1]
    recovery_time_seconds = (
        sum(u.result.duration_seconds for u in recovered) / len(recovered)
        if recovered
        else 0.0
    )

    recovery_rate = successful_units / total_units if total_units else 0.0

    expected_rows = sum(EXPECTED_ROWS_PER_SOURCE.get(u.source_hint, 0) for u in units)
    actual_rows = sum(_row_count(u) for u in successful)
    data_completeness = actual_rows / expected_rows if expected_rows else 0.0

    return ReliabilityMetrics(
        recovery_rate=recovery_rate,
        recovery_time_seconds=recovery_time_seconds,
        runtime_seconds=runtime_seconds,
        api_calls=len(fault_log.records),
        data_completeness=data_completeness,
        total_units=total_units,
        successful_units=successful_units,
    )
