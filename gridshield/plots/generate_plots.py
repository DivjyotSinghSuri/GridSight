"""Generates one comparison plot per metric for every experiment, from its scenarios' statistics.csv files.

No manual processing is required: every scenario a
:class:`~gridshield.benchmark.runner.BenchmarkRunner` runs already writes
``statistics.csv`` (mean/std/95% CI per metric) into its own permanent,
timestamped ``runs/<run_id>/`` directory; this module resolves each
scenario's ``latest.json`` pointer to find its most recent run, combines
those per experiment, and renders one bar-chart-with-error-bars PNG per
metric, comparing all of that experiment's scenarios side by side.
"""

import json
from pathlib import Path
from typing import List, Optional

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402  (backend must be set before this import)
import pandas as pd  # noqa: E402

from gridshield.configs.settings import EXPERIMENTS_OUTPUT_DIR  # noqa: E402

_NON_EXPERIMENT_DIRS = {"checkpoints", "bronze_sim"}
"""Legacy subdirectories of gridshield/outputs/ that are never experiment output folders."""


def _latest_statistics_path(scenario_dir: Path) -> Optional[Path]:
    """Resolve a scenario directory's ``latest.json`` pointer to its most recent run's ``statistics.csv``.

    Args:
        scenario_dir: path to ``gridshield/outputs/<experiment_id>/<scenario_id>/``.

    Returns:
        Path | None: the latest run's ``statistics.csv`` path, or ``None``
        if the scenario has never completed a run (no ``latest.json``) or
        that run has no ``statistics.csv`` yet.
    """
    latest_path = scenario_dir / "latest.json"
    if not latest_path.exists():
        return None
    with open(latest_path) as f:
        run_id = json.load(f).get("run_id")
    if not run_id:
        return None
    stats_path = scenario_dir / "runs" / run_id / "statistics.csv"
    return stats_path if stats_path.exists() else None


def _load_experiment_statistics(experiment_dir: Path) -> pd.DataFrame:
    """Load and combine every scenario's latest-run ``statistics.csv`` under one experiment's output directory.

    Args:
        experiment_dir: path to ``gridshield/outputs/<experiment_id>/``.

    Returns:
        pd.DataFrame: one row per (scenario_id, metric), combining each
        scenario's most recent run's ``statistics.csv`` with a
        ``scenario_id`` column added; empty if no scenario has produced
        results yet.
    """
    rows = []
    for scenario_dir in sorted(experiment_dir.iterdir()):
        if not scenario_dir.is_dir() or scenario_dir.name in _NON_EXPERIMENT_DIRS:
            continue
        stats_path = _latest_statistics_path(scenario_dir)
        if stats_path is None:
            continue
        stats_df = pd.read_csv(stats_path)
        stats_df["scenario_id"] = scenario_dir.name
        rows.append(stats_df)

    if not rows:
        return pd.DataFrame()
    return pd.concat(rows, ignore_index=True)


def generate_experiment_plots(
    experiment_id: str, output_root: Path = EXPERIMENTS_OUTPUT_DIR
) -> List[Path]:
    """Generate one bar-chart-with-error-bars PNG per metric, comparing all scenarios in an experiment.

    Args:
        experiment_id: the experiment whose scenarios to plot; its output
            directory must already contain at least one scenario with a
            ``statistics.csv``.
        output_root: base GridShield outputs directory.

    Returns:
        list[Path]: paths to the PNG files written, one per metric found;
        empty if the experiment has no results yet.
    """
    experiment_dir = output_root / experiment_id
    combined = _load_experiment_statistics(experiment_dir)
    if combined.empty:
        return []

    plots_dir = experiment_dir / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)

    written = []
    for metric, group in combined.groupby("metric"):
        # Scenarios where this metric was never computed (e.g. detection_rate
        # under validation_strategy: none) have n=0 / mean=NaN; drop them so
        # they're omitted from the chart instead of rendering as a
        # misleading zero-height bar indistinguishable from an actual 0.0.
        group = group[group["n"] > 0].sort_values("scenario_id")
        if group.empty:
            continue

        fig, ax = plt.subplots(figsize=(max(6, 0.4 * len(group)), 5))

        lower_error = (group["mean"] - group["ci_95_lower"]).clip(lower=0)
        upper_error = (group["ci_95_upper"] - group["mean"]).clip(lower=0)

        ax.bar(
            range(len(group)), group["mean"], yerr=[lower_error, upper_error],
            capsize=3, color="#4C72B0",
        )
        ax.set_ylabel(metric)
        n = int(group["n"].iloc[0]) if not group["n"].empty else 0
        ax.set_title(f"{experiment_id}: {metric} (mean, 95% CI, n={n})")
        ax.set_xticks(range(len(group)))
        ax.set_xticklabels(group["scenario_id"], rotation=75, ha="right", fontsize=7)
        fig.tight_layout()

        out_path = plots_dir / f"{metric}.png"
        fig.savefig(out_path, dpi=150)
        plt.close(fig)
        written.append(out_path)

    return written


def generate_all_plots(output_root: Path = EXPERIMENTS_OUTPUT_DIR) -> List[Path]:
    """Generate plots for every experiment that has produced output under ``output_root``.

    Args:
        output_root: base GridShield outputs directory.

    Returns:
        list[Path]: all PNG paths written, across every experiment found.
    """
    written: List[Path] = []
    if not output_root.exists():
        return written

    for experiment_dir in sorted(output_root.iterdir()):
        if not experiment_dir.is_dir() or experiment_dir.name in _NON_EXPERIMENT_DIRS:
            continue
        written.extend(generate_experiment_plots(experiment_dir.name, output_root))

    return written


if __name__ == "__main__":
    for path in generate_all_plots():
        print(f"wrote {path}")
