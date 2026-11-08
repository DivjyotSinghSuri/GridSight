"""Deterministic synthetic data-quality corruption used to establish ground truth for Experiment 2.

GridShield's :class:`~gridshield.fault_injection.injector.FaultInjector`
simulates HTTP-layer faults during ingestion — a faulted call either raises
or is retried, so corrupted data never lands in bronze storage. Measuring
the Validation Layer's *detection rate* (Experiment 2) requires the
opposite: known-bad data that DOES land in the dataset, so each of
GridShield's 8 validation checks can be verified to catch what it claims
to catch. This module deterministically corrupts a copy of a fetched
DataFrame in one specific way, returning both the corrupted DataFrame and
the validation check_name expected to flag it (the ground truth
:func:`~gridshield.metrics.validation_metrics.compute_validation_metrics`
compares detected failures against).
"""

import random
from datetime import timedelta
from typing import Dict, Optional, Tuple

import pandas as pd

NUMERIC_COLUMN_BY_SOURCE: Dict[str, str] = {
    "weather": "temperature_2m",
    "irradiance": "shortwave_radiation",
    "generation": "generation_mw",
}
"""The numeric column corrupted for range/datatype/null violations, per source."""

TIMESTAMP_COLUMN_BY_SOURCE: Dict[str, str] = {
    "weather": "time",
    "irradiance": "time",
    "daylight": "time",
    "generation": "timestamp",
}
"""The timestamp column corrupted for timestamp-related violations, per source."""

VIOLATION_TYPES = (
    "none",
    "null_values",
    "duplicate_timestamps",
    "missing_rows",
    "schema_mismatch",
    "invalid_numeric_range",
    "wrong_datatype",
    "future_timestamps",
    "freshness_violation",
)
"""All violation types this module can inject, matching GridShield's 8 required checks plus "none"."""


def corrupt_dataframe(
    df: pd.DataFrame, source: str, violation_type: str, seed: int
) -> Tuple[pd.DataFrame, Optional[str]]:
    """Deterministically corrupt a copy of ``df`` in one specific way.

    Args:
        df: the clean DataFrame to corrupt; never modified in place.
        source: one of ``"weather"``, ``"irradiance"``, ``"daylight"``, ``"generation"``.
        violation_type: one of :data:`VIOLATION_TYPES`.
        seed: seed controlling which row(s) are corrupted, for reproducibility.

    A benchmark scenario applies one ``violation_type`` uniformly across a
    mix of sources (weather, irradiance, daylight, generation), but not
    every violation type has a configured column for every source (e.g.
    daylight has no numeric column, so numeric-range/datatype violations
    don't apply to it). In that case this is a deliberate no-op — it
    returns an unchanged copy with ``None`` — rather than an error, so
    callers can invoke it unconditionally in a loop over heterogeneous
    sources.

    Returns:
        tuple[pd.DataFrame, str | None]: the corrupted DataFrame, and the
        check_name expected to flag it. ``None`` means nothing was
        injected, either because ``violation_type`` is ``"none"``, ``df``
        is empty, or ``violation_type`` has no applicable column for
        ``source``.

    Raises:
        ValueError: if ``violation_type`` is not one of :data:`VIOLATION_TYPES`.
    """
    if violation_type not in VIOLATION_TYPES:
        raise ValueError(f"Unknown violation_type: {violation_type}")

    corrupted = df.copy()
    if violation_type == "none" or corrupted.empty:
        return corrupted, None

    rng = random.Random(seed)
    ts_col = TIMESTAMP_COLUMN_BY_SOURCE.get(source)
    numeric_col = NUMERIC_COLUMN_BY_SOURCE.get(source)

    if violation_type == "null_values" and numeric_col:
        idx = rng.choice(list(corrupted.index))
        corrupted.loc[idx, numeric_col] = None
    elif violation_type == "duplicate_timestamps" and ts_col:
        corrupted = pd.concat([corrupted, corrupted.iloc[[0]]], ignore_index=True)
    elif violation_type == "missing_rows":
        corrupted = corrupted.iloc[0:0]
    elif violation_type == "schema_mismatch" and numeric_col:
        corrupted = corrupted.drop(columns=[numeric_col])
    elif violation_type == "invalid_numeric_range" and numeric_col:
        idx = rng.choice(list(corrupted.index))
        corrupted.loc[idx, numeric_col] = 999_999.0
    elif violation_type == "wrong_datatype" and numeric_col:
        corrupted[numeric_col] = corrupted[numeric_col].astype(str)
    elif violation_type == "future_timestamps" and ts_col:
        idx = rng.choice(list(corrupted.index))
        corrupted.loc[idx, ts_col] = (pd.Timestamp.now() + timedelta(days=365)).isoformat()
    elif violation_type == "freshness_violation" and ts_col:
        # Shift every row back by the same fixed offset, rather than overwriting the
        # whole column with one identical value -- that would make every row's
        # timestamp equal, spuriously triggering duplicate_timestamps as well
        # whenever the source has more than one row. Both FreshnessCheck (Python)
        # and the `freshness` dbt macro only look at max(), so shifting still makes
        # the latest record ~365 days stale while preserving row-to-row uniqueness.
        corrupted[ts_col] = (pd.to_datetime(corrupted[ts_col]) - timedelta(days=365)).astype(str)
    else:
        return df.copy(), None

    return corrupted, violation_type
