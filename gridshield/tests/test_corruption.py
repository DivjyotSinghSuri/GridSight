"""Tests confirming corrupt_dataframe() reliably triggers the validation check it claims to."""

import pandas as pd
import pytest

from gridshield.validation.corruption import VIOLATION_TYPES, corrupt_dataframe
from gridshield.validation.python_validation.checks import build_default_checks
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


@pytest.mark.parametrize("violation_type", [v for v in VIOLATION_TYPES if v != "none"])
def test_each_violation_type_is_detected_by_its_matching_check(violation_type):
    corrupted, expected_check = corrupt_dataframe(
        _clean_weather_df(), "weather", violation_type, seed=1
    )
    assert expected_check == violation_type

    report = PythonValidator(build_default_checks("weather")).validate(corrupted)
    failed_checks = {r.check_name for r in report.results if not r.passed}
    assert expected_check in failed_checks


def test_none_violation_leaves_data_clean():
    corrupted, expected_check = corrupt_dataframe(_clean_weather_df(), "weather", "none", seed=1)
    assert expected_check is None
    report = PythonValidator(build_default_checks("weather")).validate(corrupted)
    assert report.all_passed is True


def test_inapplicable_violation_type_is_a_noop_not_an_error():
    # daylight has no configured numeric column, so a numeric-range violation cannot apply.
    daylight_df = pd.DataFrame(
        {
            "time": ["2026-07-25"],
            "sunrise": ["2026-07-25T05:12"],
            "sunset": ["2026-07-25T21:04"],
            "daylight_duration": [57120.0],
            "sunshine_duration": [41230.5],
        }
    )
    corrupted, expected_check = corrupt_dataframe(
        daylight_df, "daylight", "invalid_numeric_range", seed=1
    )
    assert expected_check is None
    pd.testing.assert_frame_equal(corrupted, daylight_df)


def test_unknown_violation_type_raises():
    with pytest.raises(ValueError):
        corrupt_dataframe(_clean_weather_df(), "weather", "not_a_real_violation", seed=1)


def test_corruption_is_deterministic_given_the_same_seed():
    first, _ = corrupt_dataframe(_clean_weather_df(), "weather", "null_values", seed=7)
    second, _ = corrupt_dataframe(_clean_weather_df(), "weather", "null_values", seed=7)
    pd.testing.assert_frame_equal(first, second)


def test_freshness_violation_preserves_timestamp_uniqueness():
    # Found via a full-suite sanity pass: overwriting every row with one identical
    # stale timestamp made freshness_violation spuriously trip duplicate_timestamps
    # too, on any source with more than one row. Shifting each row back by a fixed
    # offset must still make the check fire, without manufacturing duplicates.
    corrupted, expected_check = corrupt_dataframe(
        _clean_weather_df(), "weather", "freshness_violation", seed=1
    )
    assert expected_check == "freshness_violation"
    assert corrupted["time"].nunique() == len(corrupted)

    report = PythonValidator(build_default_checks("weather")).validate(corrupted)
    failed_checks = {r.check_name for r in report.results if not r.passed}
    assert failed_checks == {"freshness_violation"}
