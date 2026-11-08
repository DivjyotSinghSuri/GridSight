"""Computes mean, standard deviation, and 95% confidence intervals across a scenario's repetitions."""

import math
from typing import List, Tuple

import pandas as pd

try:
    from scipy import stats as _scipy_stats
except ImportError:  # pragma: no cover - scipy ships transitively via scikit-learn
    _scipy_stats = None


def _confidence_interval_95(values: pd.Series) -> Tuple[float, float]:
    """Compute a 95% confidence interval for the mean of ``values``.

    Uses the t-distribution (appropriate for GridShield's typical
    n=15 repetitions) when SciPy is available, falling back to the normal
    (z=1.96) approximation otherwise.

    Args:
        values: the sample of repeated-measurement values.

    Returns:
        tuple[float, float]: ``(lower_bound, upper_bound)``. Both equal the
        sample mean if there are fewer than 2 observations.
    """
    n = len(values)
    if n < 2:
        mean = float(values.mean()) if n else float("nan")
        return (mean, mean)

    mean = float(values.mean())
    sem = float(values.std(ddof=1)) / math.sqrt(n)

    if _scipy_stats is not None:
        margin = sem * float(_scipy_stats.t.ppf(0.975, df=n - 1))
    else:
        margin = sem * 1.96

    return (mean - margin, mean + margin)


def aggregate_statistics(results_df: pd.DataFrame, metric_columns: List[str]) -> pd.DataFrame:
    """Compute mean, standard deviation, and 95% CI for each metric column across repetitions.

    Args:
        results_df: one row per repetition (matching the schema written to
            a scenario's ``results.csv``).
        metric_columns: numeric column names to summarize.

    Returns:
        pd.DataFrame: one row per metric, with columns
        ``metric, n, mean, std, ci_95_lower, ci_95_upper``. Columns absent
        from ``results_df`` are silently skipped.
    """
    rows = []
    for column in metric_columns:
        if column not in results_df.columns:
            continue
        values = results_df[column].dropna()
        lower, upper = _confidence_interval_95(values)
        rows.append(
            {
                "metric": column,
                "n": len(values),
                "mean": float(values.mean()) if len(values) else float("nan"),
                "std": float(values.std(ddof=1)) if len(values) > 1 else 0.0,
                "ci_95_lower": lower,
                "ci_95_upper": upper,
            }
        )
    return pd.DataFrame(rows)
