"""Tests for compute_reliability_metrics, in particular that data_completeness is
genuinely distinct from recovery_rate (audit Critical Issue #5)."""

import pandas as pd

from gridshield.fault_injection.experiment_log import ExperimentLog
from gridshield.fault_injection.fixture_shapes import EXPECTED_ROWS_PER_SOURCE
from gridshield.metrics.reliability_metrics import compute_reliability_metrics
from gridshield.wrappers.base import WrapperResult
from gridshield.wrappers.ingestion_wrapper import IngestionUnit


def _unit(source: str, success: bool, n_rows: int) -> IngestionUnit:
    value = pd.DataFrame({"x": range(n_rows)}) if success and n_rows else None
    return IngestionUnit(
        f"{source}:k", source, WrapperResult(success=success, attempts=1, duration_seconds=0.1, value=value)
    )


def _empty_log() -> ExperimentLog:
    return ExperimentLog(scenario_id="s", run_number=0, seed=1, fault_type=None, fault_probability=0.0)


def test_expected_rows_per_source_matches_fixtures():
    assert EXPECTED_ROWS_PER_SOURCE == {"weather": 6, "irradiance": 6, "daylight": 1, "generation": 4}


def test_recovery_rate_and_data_completeness_are_equal_when_failures_are_uniform():
    units = [_unit("weather", True, 6), _unit("weather", False, 0)]  # 1/2 units, uniform source
    m = compute_reliability_metrics(units, _empty_log(), runtime_seconds=1.0)
    assert m.recovery_rate == 0.5
    assert m.data_completeness == 0.5


def test_recovery_rate_and_data_completeness_diverge_under_differential_source_failure():
    # weather x2 (6 rows each), irradiance x2 (6 rows each), daylight x1 (1 row), generation fails (4 rows lost)
    units = [
        _unit("weather", True, 6), _unit("weather", True, 6),
        _unit("irradiance", True, 6), _unit("irradiance", True, 6),
        _unit("daylight", True, 1),
        _unit("generation", False, 0),
    ]
    m = compute_reliability_metrics(units, _empty_log(), runtime_seconds=1.0)

    assert m.recovery_rate == 5 / 6
    assert m.data_completeness == 25 / 29
    assert m.recovery_rate != m.data_completeness


def test_all_units_fail_yields_zero_for_both_metrics():
    units = [_unit("weather", False, 0), _unit("generation", False, 0)]
    m = compute_reliability_metrics(units, _empty_log(), runtime_seconds=1.0)
    assert m.recovery_rate == 0.0
    assert m.data_completeness == 0.0


def test_empty_units_list_does_not_divide_by_zero():
    m = compute_reliability_metrics([], _empty_log(), runtime_seconds=1.0)
    assert m.recovery_rate == 0.0
    assert m.data_completeness == 0.0
    assert m.total_units == 0


def test_resumed_from_checkpoint_units_are_credited_their_expected_row_count():
    # A checkpoint-resumed unit has no .value (nothing was re-fetched), but it
    # genuinely completed in an earlier pass — it must count fully toward
    # data_completeness, not as 0 rows (which would understate completeness
    # specifically for the checkpointing strategy this metric most needs to be fair to).
    resumed_result = WrapperResult(
        success=True, attempts=0, duration_seconds=0.0, value=None, resumed_from_checkpoint=True
    )
    units = [IngestionUnit("weather:k", "weather", resumed_result)]
    m = compute_reliability_metrics(units, _empty_log(), runtime_seconds=1.0)
    assert m.recovery_rate == 1.0
    assert m.data_completeness == 1.0  # credited the full 6 expected weather rows, not 0
