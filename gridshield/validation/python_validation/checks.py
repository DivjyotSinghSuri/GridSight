"""The eight Python validation checks GridShield's methodology requires.

These run before transformation, directly against the DataFrames returned
by GridSight's unmodified ``fetch_*`` functions. Each check mirrors one of
the custom dbt generic tests in
``gridshield/validation/dbt/macros/generic_tests.sql``, so Experiment 2 can
fairly compare detection behaviour between the two engines.
"""

from typing import Dict, List

import pandas as pd

from gridshield.validation.base import ValidationResult
from gridshield.validation.python_validation.base import ValidationCheck

_RAW_SOURCE_SCHEMAS: Dict[str, List[str]] = {
    "weather": [
        "time", "temperature_2m", "relative_humidity_2m", "precipitation",
        "cloud_cover", "wind_speed_10m", "wind_direction_10m",
    ],
    "irradiance": [
        "time", "shortwave_radiation", "direct_radiation",
        "diffuse_radiation", "direct_normal_irradiance",
    ],
    "daylight": ["time", "sunrise", "sunset", "daylight_duration", "sunshine_duration"],
    "generation": ["timestamp", "production_type", "generation_mw"],
}
"""Expected raw (pre-transform) column list per GridSight ingestion source."""

_DTYPE_KIND_ALIASES = {
    "float": "f",
    "int": "i",
    "object": "O",
    "string": "O",
    "datetime": "M",
}
"""Maps friendly datatype names to pandas' single-character dtype 'kind' codes."""


class NullCheck(ValidationCheck):
    """Fails if any of the configured columns contain NULL/NaN values."""

    name = "null_values"

    def __init__(self, columns: List[str]):
        """Args:
        columns: column names to check for nulls.
        """
        self.columns = columns

    def run(self, df: pd.DataFrame) -> ValidationResult:
        """Count NULL/NaN values across ``self.columns``."""
        missing_columns = [c for c in self.columns if c not in df.columns]
        if missing_columns:
            return ValidationResult(
                self.name, "python", False, len(missing_columns),
                f"columns missing entirely: {missing_columns}",
            )
        null_count = int(df[self.columns].isnull().sum().sum())
        return ValidationResult(
            self.name, "python", null_count == 0, null_count,
            f"{null_count} null value(s) across {self.columns}",
        )


class DuplicateTimestampCheck(ValidationCheck):
    """Fails if the configured timestamp column contains duplicate values."""

    name = "duplicate_timestamps"

    def __init__(self, timestamp_column: str):
        """Args:
        timestamp_column: name of the column to check for duplicates.
        """
        self.timestamp_column = timestamp_column

    def run(self, df: pd.DataFrame) -> ValidationResult:
        """Count duplicated values in ``self.timestamp_column``."""
        if self.timestamp_column not in df.columns:
            return ValidationResult(
                self.name, "python", False, 0, f"column {self.timestamp_column} missing"
            )
        duplicate_count = int(df[self.timestamp_column].duplicated().sum())
        return ValidationResult(
            self.name, "python", duplicate_count == 0, duplicate_count,
            f"{duplicate_count} duplicate timestamp(s) in {self.timestamp_column}",
        )


class MissingRowsCheck(ValidationCheck):
    """Fails if the dataset has fewer than the configured minimum number of rows."""

    name = "missing_rows"

    def __init__(self, min_rows: int = 1):
        """Args:
        min_rows: minimum acceptable row count.
        """
        self.min_rows = min_rows

    def run(self, df: pd.DataFrame) -> ValidationResult:
        """Compare ``len(df)`` against ``self.min_rows``."""
        actual_rows = len(df)
        shortfall = max(0, self.min_rows - actual_rows)
        return ValidationResult(
            self.name, "python", shortfall == 0, shortfall,
            f"{actual_rows} row(s), expected at least {self.min_rows}",
        )


class SchemaCheck(ValidationCheck):
    """Fails if the dataset's columns don't exactly match the expected column list."""

    name = "schema_mismatch"

    def __init__(self, expected_columns: List[str]):
        """Args:
        expected_columns: the exact set of column names expected.
        """
        self.expected_columns = expected_columns

    def run(self, df: pd.DataFrame) -> ValidationResult:
        """Diff ``df.columns`` against ``self.expected_columns``."""
        actual_columns = list(df.columns)
        missing = [c for c in self.expected_columns if c not in actual_columns]
        extra = [c for c in actual_columns if c not in self.expected_columns]
        violation_count = len(missing) + len(extra)
        return ValidationResult(
            self.name, "python", violation_count == 0, violation_count,
            f"missing={missing}, extra={extra}",
        )


class RangeCheck(ValidationCheck):
    """Fails if any value in the configured column falls outside [min_value, max_value]."""

    name = "invalid_numeric_range"

    def __init__(self, column: str, min_value: float, max_value: float):
        """Args:
        column: numeric column to range-check.
        min_value: inclusive lower bound.
        max_value: inclusive upper bound.
        """
        self.column = column
        self.min_value = min_value
        self.max_value = max_value

    def run(self, df: pd.DataFrame) -> ValidationResult:
        """Count values in ``self.column`` outside ``[min_value, max_value]``.

        Non-numeric values (e.g. if the column was corrupted to the wrong
        datatype) are coerced with ``pd.to_numeric(errors="coerce")``; any
        that fail to coerce count as out-of-range rather than crashing the
        comparison.
        """
        if self.column not in df.columns:
            return ValidationResult(self.name, "python", False, 0, f"column {self.column} missing")
        raw = df[self.column].dropna()
        numeric = pd.to_numeric(raw, errors="coerce")
        unparseable = int(numeric.isna().sum())
        parseable = numeric.dropna()
        out_of_range = parseable[(parseable < self.min_value) | (parseable > self.max_value)]
        count = len(out_of_range) + unparseable
        return ValidationResult(
            self.name, "python", count == 0, count,
            f"{count} value(s) outside [{self.min_value}, {self.max_value}] in {self.column}",
        )


class DatatypeCheck(ValidationCheck):
    """Fails if the configured column's dtype does not match the expected kind."""

    name = "wrong_datatype"

    def __init__(self, column: str, expected_kind: str):
        """Args:
        column: column to check.
        expected_kind: one of ``"float"``, ``"int"``, ``"object"``/``"string"``, ``"datetime"``.
        """
        self.column = column
        self.expected_kind = expected_kind

    def run(self, df: pd.DataFrame) -> ValidationResult:
        """Compare ``df[column].dtype.kind`` against the expected dtype kind."""
        if self.column not in df.columns:
            return ValidationResult(self.name, "python", False, 0, f"column {self.column} missing")
        actual_kind = df[self.column].dtype.kind
        expected_kind = _DTYPE_KIND_ALIASES.get(self.expected_kind, self.expected_kind)
        passed = actual_kind == expected_kind
        return ValidationResult(
            self.name, "python", passed, 0 if passed else 1,
            f"{self.column}: actual dtype kind={actual_kind!r}, expected={expected_kind!r}",
        )


class FutureTimestampCheck(ValidationCheck):
    """Fails if any value in the configured timestamp column is later than the current time."""

    name = "future_timestamps"

    def __init__(self, timestamp_column: str):
        """Args:
        timestamp_column: name of the timestamp column to check.
        """
        self.timestamp_column = timestamp_column

    def run(self, df: pd.DataFrame) -> ValidationResult:
        """Count values in ``self.timestamp_column`` later than now."""
        if self.timestamp_column not in df.columns:
            return ValidationResult(
                self.name, "python", False, 0, f"column {self.timestamp_column} missing"
            )
        parsed = pd.to_datetime(df[self.timestamp_column], errors="coerce")
        future_count = int((parsed > pd.Timestamp.now()).sum())
        return ValidationResult(
            self.name, "python", future_count == 0, future_count,
            f"{future_count} future timestamp(s) in {self.timestamp_column}",
        )


class FreshnessCheck(ValidationCheck):
    """Fails if the most recent value in the configured timestamp column is older than ``max_age_hours``."""

    name = "freshness_violation"

    def __init__(self, timestamp_column: str, max_age_hours: float):
        """Args:
        timestamp_column: name of the timestamp column to assess.
        max_age_hours: maximum acceptable age, in hours, of the most recent record.
        """
        self.timestamp_column = timestamp_column
        self.max_age_hours = max_age_hours

    def run(self, df: pd.DataFrame) -> ValidationResult:
        """Compare the age of the most recent ``self.timestamp_column`` value against ``max_age_hours``."""
        if self.timestamp_column not in df.columns or df.empty:
            return ValidationResult(self.name, "python", False, 0, "no data to assess freshness")
        parsed = pd.to_datetime(df[self.timestamp_column], errors="coerce")
        latest = parsed.max()
        if pd.isna(latest):
            return ValidationResult(self.name, "python", False, 0, "no parseable timestamps")
        age_hours = (pd.Timestamp.now() - latest).total_seconds() / 3600
        passed = age_hours <= self.max_age_hours
        return ValidationResult(
            self.name, "python", passed, 0 if passed else 1,
            f"latest record is {age_hours:.1f}h old (threshold {self.max_age_hours}h)",
        )


def build_default_checks(source: str) -> List[ValidationCheck]:
    """Build GridShield's default set of Python validation checks for one raw ingestion source.

    Runs before transformation, against the exact column shapes GridSight's
    ``fetch_weather``/``fetch_irradiance``/``fetch_daylight``/``fetch_generation``
    return.

    Args:
        source: one of ``"weather"``, ``"irradiance"``, ``"daylight"``, ``"generation"``.

    Returns:
        list[ValidationCheck]: the checks a :class:`~gridshield.validation.python_validation.validator.PythonValidator`
        should run against that source's raw fetch DataFrame.

    Raises:
        ValueError: if ``source`` is not recognized.
    """
    if source not in _RAW_SOURCE_SCHEMAS:
        raise ValueError(f"Unknown source: {source}")

    schema = _RAW_SOURCE_SCHEMAS[source]
    timestamp_column = "timestamp" if source == "generation" else "time"

    checks: List[ValidationCheck] = [
        NullCheck([timestamp_column]),
        DuplicateTimestampCheck(timestamp_column),
        MissingRowsCheck(min_rows=1),
        SchemaCheck(schema),
        FutureTimestampCheck(timestamp_column),
    ]

    if source == "weather":
        checks += [
            NullCheck(["temperature_2m"]),
            RangeCheck("temperature_2m", -50, 60),
            RangeCheck("relative_humidity_2m", 0, 100),
            DatatypeCheck("temperature_2m", "float"),
            FreshnessCheck(timestamp_column, max_age_hours=720),
        ]
    elif source == "irradiance":
        checks += [
            NullCheck(["shortwave_radiation"]),
            RangeCheck("shortwave_radiation", 0, 1500),
            DatatypeCheck("shortwave_radiation", "float"),
        ]
    elif source == "generation":
        checks += [
            NullCheck(["generation_mw"]),
            RangeCheck("generation_mw", 0, 100000),
            DatatypeCheck("generation_mw", "float"),
        ]

    return checks
