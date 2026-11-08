"""Command-line entry point for the NO-RESILIENCE BASELINE experiment.

Runs the exact same scenario matrices as ``experiment_1_reliability`` and
``experiment_3_full_methodology`` (the only two frozen-benchmark experiments
where GridSight's internal fetcher-level retry logic is ever exercised —
Experiments 2 and 4 hold ``fault_probability: 0.0`` throughout), from the
mirrored configs under
``gridshield/configs/experiments_no_resilience_baseline/``, with GridSight's
own internal resilience mechanism disabled via
``disable_gridsight_internal_resilience()``. GridShield's own reliability
strategies and validation engines are completely unmodified — the only
experimental variable is whether GridSight's fetchers get to silently
absorb a fault before GridShield's layer is ever invoked.

Output is written to ``gridshield/outputs_no_resilience_baseline/``, a
directory that is never read or written by the existing resilient
experiment's code paths, so the frozen resilient dataset under
``gridshield/outputs/`` is never touched.

Examples:
    Sanity pass (1 repetition per scenario, mirrors the project's own
    documented sanity-check-before-committing protocol, handbook Ch.15/17)::

        python -m gridshield.benchmark.cli_no_resilience_baseline --sanity

    Full run (15 repetitions per scenario, matching the resilient
    experiment's repetition count exactly)::

        python -m gridshield.benchmark.cli_no_resilience_baseline
"""

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from gridshield.benchmark.runner import BenchmarkRunner
from gridshield.benchmark.scenario import Scenario, load_scenarios_from_yaml
from gridshield.configs.paths import GRIDSHIELD_ROOT
from gridshield.fault_injection.internal_resilience_toggle import (
    disable_gridsight_internal_resilience,
)
from gridshield.plots.generate_plots import generate_all_plots

CONFIGS_DIR = GRIDSHIELD_ROOT / "configs" / "experiments_no_resilience_baseline"
OUTPUT_ROOT = GRIDSHIELD_ROOT / "outputs_no_resilience_baseline"

CONFIG_FILES = [
    CONFIGS_DIR / "experiment_1_reliability_no_resilience_baseline.yaml",
    CONFIGS_DIR / "experiment_3_full_methodology_no_resilience_baseline.yaml",
]


def _load_all_scenarios() -> List[Scenario]:
    """Load every scenario from both no-resilience-baseline config files, in file order."""
    scenarios: List[Scenario] = []
    for path in CONFIG_FILES:
        scenarios.extend(load_scenarios_from_yaml(path))
    return scenarios


def main(argv: Optional[List[str]] = None) -> int:
    """Parse CLI arguments and run every no-resilience-baseline scenario.

    Args:
        argv: argument list to parse; defaults to ``sys.argv[1:]``.

    Returns:
        int: process exit code (0 on success, 1 if any scenario failed).
    """
    parser = argparse.ArgumentParser(
        description="Run the NO-RESILIENCE BASELINE mirror of Experiments 1 and 3."
    )
    parser.add_argument(
        "--sanity",
        action="store_true",
        help="Override every scenario's repetitions to 1 for a fast sanity pass "
        "(mirrors the project's own sanity-check-before-committing protocol). "
        "Writes to its own run directories; does not consume or overwrite the full-run data.",
    )
    parser.add_argument(
        "--scenario", help="Run only this scenario_id, across both config files."
    )
    parser.add_argument(
        "--list", action="store_true", help="List resolved scenarios and exit without running them."
    )
    args = parser.parse_args(argv)

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    scenarios = _load_all_scenarios()

    if args.scenario:
        scenarios = [s for s in scenarios if s.scenario_id == args.scenario]
        if not scenarios:
            raise SystemExit(f"No scenario named {args.scenario!r} in the no-resilience-baseline configs")

    if args.sanity:
        for scenario in scenarios:
            scenario.repetitions = 1

    if args.list:
        for scenario in scenarios:
            print(f"{scenario.experiment_id}/{scenario.scenario_id} (repetitions={scenario.repetitions})")
        return 0

    if not scenarios:
        print("No scenarios matched.", file=sys.stderr)
        return 1

    failed: List[str] = []
    with disable_gridsight_internal_resilience():
        for scenario in scenarios:
            label = f"{scenario.experiment_id}/{scenario.scenario_id}"
            print(f"Running {label} ({scenario.repetitions} repetitions)...", flush=True)
            try:
                BenchmarkRunner(scenario, output_root=OUTPUT_ROOT).run()
            except Exception as exc:  # noqa: BLE001 - one scenario's failure must not abort the rest
                print(f"FAILED: {label}: {exc}", file=sys.stderr, flush=True)
                failed.append(label)
                continue
            print(f"Done: {label}", flush=True)

    if not args.sanity:
        written = generate_all_plots(output_root=OUTPUT_ROOT)
        for path in written:
            print(f"wrote {path}")

    if failed:
        print(f"\n{len(failed)}/{len(scenarios)} scenario(s) failed:", file=sys.stderr)
        for label in failed:
            print(f"  - {label}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
