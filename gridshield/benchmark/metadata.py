"""Collects machine-readable run metadata (git commit, environment, scenario config) for reproducibility."""

import platform
import subprocess
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from typing import Any, Dict

from gridshield.benchmark.scenario import Scenario
from gridshield.configs.paths import GRIDSIGHT_ROOT

_TRACKED_PACKAGES = (
    "requests", "pandas", "duckdb", "dbt-core", "dbt-duckdb",
    "numpy", "scipy", "pyyaml", "boto3", "python-dotenv",
)
"""Packages whose installed versions are recorded in every run's metadata.json."""


def _git_commit_hash() -> str:
    """Return the current git commit hash of the GridSight repository, or ``"unknown"`` if unavailable.

    Best-effort: never raises, since metadata collection must not block a
    benchmark run just because git is unavailable.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=GRIDSIGHT_ROOT,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return "unknown"


def _package_versions() -> Dict[str, str]:
    """Look up the installed version of every package in :data:`_TRACKED_PACKAGES`.

    Returns:
        dict[str, str]: package name to version string, or ``"not installed"``.
    """
    versions = {}
    for package in _TRACKED_PACKAGES:
        try:
            versions[package] = version(package)
        except PackageNotFoundError:
            versions[package] = "not installed"
    return versions


def collect_run_metadata(scenario: Scenario) -> Dict[str, Any]:
    """Collect everything needed to reproduce a scenario's benchmark run.

    Args:
        scenario: the scenario about to be (or being) run.

    Returns:
        dict: containing ``git_commit_hash``, ``timestamp``, ``scenario``,
        ``master_seed``, ``python_version``, and ``package_versions``.
    """
    return {
        "git_commit_hash": _git_commit_hash(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "scenario": scenario.as_dict(),
        "master_seed": scenario.master_seed,
        "python_version": platform.python_version(),
        "package_versions": _package_versions(),
    }
