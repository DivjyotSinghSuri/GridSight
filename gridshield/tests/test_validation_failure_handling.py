"""Tests that a dbt model-build failure during validation is recorded honestly, not fatally.

``schema_mismatch``/``missing_rows`` are severe enough to break GridShield's
staging dbt models' static SQL before ``dbt test`` ever runs (found during a
full-95-scenario, 1-repetition sanity pass ahead of the formal benchmark —
see gridshield/README.md's Known Limitations). ``BenchmarkRunner`` must
surface that as an honest ``validation_status: "dbt_run_failed"`` result row
with ``None`` detection metrics, not let the exception propagate and abort
the whole scenario (or, upstream in the CLI, the whole benchmark run).
"""

import math

from gridshield.benchmark.runner import BenchmarkRunner
from gridshield.benchmark.scenario import Scenario


def _scenario(scenario_id: str, validation_strategy: str, inject_violation: str) -> Scenario:
    return Scenario(
        scenario_id=scenario_id,
        experiment_id="experiment_2_validation",
        reliability_strategy="baseline",
        validation_strategy=validation_strategy,
        fault_type=None,
        fault_probability=0.0,
        repetitions=1,
        grid_points_limit=1,
        validation_params={"inject_violation": inject_violation},
    )


def test_schema_mismatch_under_dbt_records_honest_failure_without_raising(tmp_path):
    scenario = _scenario("dbt__schema_mismatch", "dbt", "schema_mismatch")
    df = BenchmarkRunner(scenario, output_root=tmp_path).run()  # must not raise

    row = df.iloc[0]
    assert row["validation_status"] == "dbt_run_failed"
    assert row["validation_error"]  # non-empty dbt error message captured
    assert math.isnan(row["detection_rate"])
    assert math.isnan(row["false_positive_rate"])
    assert math.isnan(row["propagation"])


def test_missing_rows_under_combined_records_honest_failure_without_raising(tmp_path):
    scenario = _scenario("combined__missing_rows", "combined", "missing_rows")
    df = BenchmarkRunner(scenario, output_root=tmp_path).run()  # must not raise

    row = df.iloc[0]
    assert row["validation_status"] == "dbt_run_failed"
    assert row["validation_error"]
    assert math.isnan(row["detection_rate"])


def test_null_values_under_dbt_still_reports_ok_status(tmp_path):
    scenario = _scenario("dbt__null_values", "dbt", "null_values")
    df = BenchmarkRunner(scenario, output_root=tmp_path).run()

    row = df.iloc[0]
    assert row["validation_status"] == "ok"
    assert row["validation_error"] is None or (isinstance(row["validation_error"], float) and math.isnan(row["validation_error"]))
    assert row["detection_rate"] == 1.0
