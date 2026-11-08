"""Tests for GridShield's eight Python validation checks and the PythonValidator."""

import pandas as pd

from gridshield.validation.python_validation.checks import (
    DatatypeCheck,
    DuplicateTimestampCheck,
    FreshnessCheck,
    FutureTimestampCheck,
    MissingRowsCheck,
    NullCheck,
    RangeCheck,
    SchemaCheck,
    build_default_checks,
)
from gridshield.validation.python_validation.validator import PythonValidator


def _clean_weather_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "time": ["2026-07-25T00:00", "2026-07-25T01:00"],
            "temperature_2m": [14.2, 13.8],
            "relative_humidity_2m": [82, 84],
            "precipitation": [0.0, 0.0],
            "cloud_cover": [45, 50],
            "wind_speed_10m": [8.3, 7.9],
            "wind_direction_10m": [210, 215],
        }
    )


def test_null_check_passes_on_clean_data():
    result = NullCheck(["temperature_2m"]).run(_clean_weather_df())
    assert result.passed is True
    assert result.violation_count == 0


def test_null_check_fails_on_null_value():
    df = _clean_weather_df()
    df.loc[0, "temperature_2m"] = None
    result = NullCheck(["temperature_2m"]).run(df)
    assert result.passed is False
    assert result.violation_count == 1


def test_duplicate_timestamp_check_detects_duplicates():
    df = pd.concat([_clean_weather_df(), _clean_weather_df().iloc[[0]]], ignore_index=True)
    result = DuplicateTimestampCheck("time").run(df)
    assert result.passed is False
    assert result.violation_count == 1


def test_missing_rows_check_respects_threshold():
    df = _clean_weather_df()
    assert MissingRowsCheck(min_rows=2).run(df).passed is True
    assert MissingRowsCheck(min_rows=5).run(df).passed is False


def test_schema_check_flags_missing_and_extra_columns():
    df = _clean_weather_df().drop(columns=["wind_direction_10m"])
    df["unexpected_column"] = 1
    result = SchemaCheck(list(_clean_weather_df().columns)).run(df)
    assert result.passed is False
    assert "wind_direction_10m" in result.message
    assert "unexpected_column" in result.message


def test_range_check_flags_out_of_range_values():
    df = _clean_weather_df()
    df.loc[0, "cloud_cover"] = 150
    result = RangeCheck("cloud_cover", 0, 100).run(df)
    assert result.passed is False
    assert result.violation_count == 1


def test_range_check_handles_non_numeric_column_gracefully():
    df = _clean_weather_df()
    df["temperature_2m"] = df["temperature_2m"].astype(str)
    result = RangeCheck("temperature_2m", -50, 60).run(df)
    assert result.passed is True  # numeric strings still coerce fine
    assert result.violation_count == 0


def test_datatype_check_detects_wrong_dtype():
    df = _clean_weather_df()
    df["temperature_2m"] = df["temperature_2m"].astype(str)
    result = DatatypeCheck("temperature_2m", "float").run(df)
    assert result.passed is False


def test_future_timestamp_check_flags_future_values():
    df = _clean_weather_df()
    df.loc[0, "time"] = "2099-01-01T00:00"
    result = FutureTimestampCheck("time").run(df)
    assert result.passed is False
    assert result.violation_count == 1


def test_freshness_check_flags_stale_data():
    df = _clean_weather_df()  # fixed 2026-07-25 timestamps, older than a 1-hour window
    result = FreshnessCheck("time", max_age_hours=1).run(df)
    assert result.passed is False


def test_build_default_checks_covers_all_sources():
    for source in ("weather", "irradiance", "daylight", "generation"):
        checks = build_default_checks(source)
        assert len(checks) >= 5


def test_python_validator_aggregates_all_check_results():
    df = _clean_weather_df()
    df.loc[0, "cloud_cover"] = 999
    validator = PythonValidator(
        [NullCheck(["temperature_2m"]), RangeCheck("cloud_cover", 0, 100)]
    )
    report = validator.validate(df)
    assert len(report.results) == 2
    assert report.all_passed is False
    assert report.violations_detected == 1
