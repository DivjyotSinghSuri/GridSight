"""Tests for the statistics aggregator's mean/std/95% CI computation."""

import pandas as pd
import pytest

from gridshield.statistics.aggregator import aggregate_statistics


def test_aggregate_statistics_matches_hand_computed_values():
    values = [1.0, 2.0, 3.0, 4.0, 5.0]
    df = pd.DataFrame({"recovery_rate": values})

    result = aggregate_statistics(df, ["recovery_rate"])
    row = result.iloc[0]

    assert row["n"] == 5
    assert row["mean"] == pytest.approx(3.0)
    assert row["std"] == pytest.approx(pd.Series(values).std(ddof=1))
    assert row["ci_95_lower"] < row["mean"] < row["ci_95_upper"]


def test_aggregate_statistics_single_observation_has_zero_width_ci():
    df = pd.DataFrame({"metric": [42.0]})
    result = aggregate_statistics(df, ["metric"])
    row = result.iloc[0]
    assert row["ci_95_lower"] == row["ci_95_upper"] == 42.0
    assert row["std"] == 0.0


def test_aggregate_statistics_skips_columns_absent_from_the_dataframe():
    df = pd.DataFrame({"present": [1.0, 2.0]})
    result = aggregate_statistics(df, ["present", "absent"])
    assert list(result["metric"]) == ["present"]


def test_aggregate_statistics_drops_nan_values_before_summarizing():
    df = pd.DataFrame({"metric": [1.0, None, 3.0]})
    result = aggregate_statistics(df, ["metric"])
    assert result.iloc[0]["n"] == 2
