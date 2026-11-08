"""Tests for DbtValidationWrapper: check-name mapping, skip handling, and failure surfacing.

These specifically close the test-coverage gap the audit identified: no
prior test exercised the dbt engine's output against
``compute_validation_metrics``'s ground-truth comparison, which is exactly
why the check-name mismatch bug (Critical Issue #1) shipped undetected.
"""

import shutil

import pandas as pd
import pytest

from gridshield.configs.settings import BRONZE_SIM_DIR, GRIDSHIELD_DB_PATH
from gridshield.wrappers.bronze_load_wrapper import load_bronze_local
from gridshield.wrappers.bronze_sink import write_bronze_local
from gridshield.wrappers.dbt_wrapper import DbtValidationWrapper


def _write_all_sources(weather_temperature_2m=(14.2, 13.8)):
    """Write a complete, valid set of bronze CSVs for all four sources (so dbt run succeeds)."""
    weather = pd.DataFrame(
        {
            "time": ["2026-07-25T00:00", "2026-07-25T01:00"],
            "temperature_2m": list(weather_temperature_2m),
            "relative_humidity_2m": [82, 84],
            "precipitation": [0.0, 0.0],
            "cloud_cover": [45, 50],
            "wind_speed_10m": [8.3, 7.9],
            "wind_direction_10m": [210, 215],
        }
    )
    irradiance = pd.DataFrame(
        {
            "time": ["2026-07-25T00:00", "2026-07-25T01:00"],
            "shortwave_radiation": [0.0, 12.5],
            "direct_radiation": [0.0, 4.1],
            "diffuse_radiation": [0.0, 8.4],
            "direct_normal_irradiance": [0.0, 21.2],
        }
    )
    daylight = pd.DataFrame(
        {
            "time": ["2026-07-25"],
            "sunrise": ["2026-07-25T05:12"],
            "sunset": ["2026-07-25T21:04"],
            "daylight_duration": [57120.0],
            "sunshine_duration": [41230.5],
        }
    )
    generation = pd.DataFrame(
        {
            "timestamp": ["2026-07-25 00:00:00", "2026-07-25 00:15:00"],
            "production_type": ["Solar", "Solar"],
            "generation_mw": [0.0, 12.4],
        }
    )
    write_bronze_local(weather, source="weather/openmeteo", filename="20260725.csv", folder="grid_01")
    write_bronze_local(irradiance, source="irradiance/openmeteo", filename="20260725.csv", folder="grid_01")
    write_bronze_local(daylight, source="daylight/openmeteo", filename="20260725.csv")
    write_bronze_local(generation, source="generation/entsoe", filename="20260725.csv")


@pytest.fixture
def clean_isolated_storage():
    """Ensure a fresh bronze_sim/DuckDB for each test, and clean up afterward."""
    shutil.rmtree(BRONZE_SIM_DIR, ignore_errors=True)
    GRIDSHIELD_DB_PATH.unlink(missing_ok=True)
    yield
    shutil.rmtree(BRONZE_SIM_DIR, ignore_errors=True)
    GRIDSHIELD_DB_PATH.unlink(missing_ok=True)


def test_dbt_detects_injected_null_with_correct_canonical_check_name(clean_isolated_storage):
    _write_all_sources(weather_temperature_2m=(14.2, None))  # inject a null
    load_bronze_local()

    wrapper = DbtValidationWrapper()
    wrapper.run_models()
    results = wrapper.run_tests()

    failed = {r.check_name for r in results if not r.passed}
    assert failed == {"null_values"}, (
        f"expected exactly {{'null_values'}} to fail, got {failed} — "
        "check-name mapping may have regressed"
    )


def test_dbt_reports_no_failures_on_clean_data(clean_isolated_storage):
    _write_all_sources()
    load_bronze_local()

    wrapper = DbtValidationWrapper()
    wrapper.run_models()
    results = wrapper.run_tests()

    assert len(results) > 0
    assert all(r.passed for r in results)


def test_dbt_check_names_use_canonical_vocabulary_not_raw_unique_ids(clean_isolated_storage):
    _write_all_sources()
    load_bronze_local()

    wrapper = DbtValidationWrapper()
    wrapper.run_models()
    results = wrapper.run_tests()

    canonical_names = {
        "null_values", "duplicate_timestamps", "missing_rows", "schema_mismatch",
        "invalid_numeric_range", "wrong_datatype", "future_timestamps", "freshness_violation",
    }
    check_names = {r.check_name for r in results}
    # every result must map to the canonical vocabulary, never a raw hash/unique_id fragment
    assert check_names <= canonical_names, f"unmapped/raw check names leaked through: {check_names - canonical_names}"


def test_run_models_raises_on_missing_bronze_tables(clean_isolated_storage):
    # Only write weather; bronze_daylight/irradiance/generation tables never get created,
    # so `dbt run` must fail loudly rather than silently letting run_tests() proceed.
    weather = pd.DataFrame(
        {
            "time": ["2026-07-25T00:00"],
            "temperature_2m": [14.2],
            "relative_humidity_2m": [82],
            "precipitation": [0.0],
            "cloud_cover": [45],
            "wind_speed_10m": [8.3],
            "wind_direction_10m": [210],
        }
    )
    write_bronze_local(weather, source="weather/openmeteo", filename="20260725.csv", folder="grid_01")
    load_bronze_local()

    wrapper = DbtValidationWrapper()
    with pytest.raises(RuntimeError, match="dbt run failed"):
        wrapper.run_models()
