"""Command-line entry point for GridShield's benchmark engine.

Examples:
    List every configured scenario::

        python -m gridshield.benchmark.cli --list

    Run one scenario::

        python -m gridshield.benchmark.cli --experiment experiment_1_reliability --scenario baseline_no_fault

    Run every scenario in one experiment::

        python -m gridshield.benchmark.cli --experiment experiment_1_reliability

    Run every scenario across every experiment::

        python -m gridshield.benchmark.cli --all
"""

import argparse
import sys
from typing import List, Optional

from gridshield.benchmark.runner import BenchmarkRunner
from gridshield.benchmark.scenario import Scenario, load_all_scenarios, load_scenarios_from_yaml
from gridshield.configs.settings import CONFIGS_EXPERIMENTS_DIR, ensure_output_dirs


def _resolve_scenarios(args: argparse.Namespace) -> List[Scenario]:
    """Determine which scenarios to run based on parsed CLI arguments.

    Args:
        args: parsed CLI arguments (see :func:`main`).

    Returns:
        list[Scenario]: the scenarios to run, in file order.

    Raises:
        SystemExit: if ``--experiment`` names a file that does not exist,
            or ``--scenario`` names a scenario that does not exist within it.
    """
    if args.experiment:
        yaml_path = CONFIGS_EXPERIMENTS_DIR / f"{args.experiment}.yaml"
        if not yaml_path.exists():
            raise SystemExit(f"No experiment config found at {yaml_path}")
        scenarios = load_scenarios_from_yaml(yaml_path)
        if args.scenario:
            scenarios = [s for s in scenarios if s.scenario_id == args.scenario]
            if not scenarios:
                raise SystemExit(f"No scenario named {args.scenario!r} in {yaml_path}")
        return scenarios
    return load_all_scenarios(CONFIGS_EXPERIMENTS_DIR)


def main(argv: Optional[List[str]] = None) -> int:
    """Parse CLI arguments and run the selected scenario(s).

    Args:
        argv: argument list to parse; defaults to ``sys.argv[1:]``.

    Returns:
        int: process exit code (0 on success, 1 if no scenarios matched).
    """
    parser = argparse.ArgumentParser(description="Run GridShield benchmark scenarios.")
    parser.add_argument(
        "--experiment",
        help="Experiment id (config filename stem under gridshield/configs/experiments/), "
        "e.g. experiment_1_reliability. Omit to select across all experiments.",
    )
    parser.add_argument(
        "--scenario", help="Run only this scenario_id within --experiment. Requires --experiment."
    )
    parser.add_argument(
        "--all", action="store_true", help="Explicit alias for running every resolved scenario."
    )
    parser.add_argument("--list", action="store_true", help="List resolved scenarios and exit without running them.")
    args = parser.parse_args(argv)

    if args.scenario and not args.experiment:
        parser.error("--scenario requires --experiment")

    ensure_output_dirs()
    scenarios = _resolve_scenarios(args)

    if args.list:
        for scenario in scenarios:
            print(f"{scenario.experiment_id}/{scenario.scenario_id}")
        return 0

    if not scenarios:
        print("No scenarios matched.", file=sys.stderr)
        return 1

    failed: List[str] = []
    for scenario in scenarios:
        label = f"{scenario.experiment_id}/{scenario.scenario_id}"
        print(f"Running {label} ({scenario.repetitions} repetitions)...")
        try:
            BenchmarkRunner(scenario).run()
        except Exception as exc:  # noqa: BLE001 - one scenario's failure must not abort the rest
            print(f"FAILED: {label}: {exc}", file=sys.stderr)
            failed.append(label)
            continue
        print(f"Done: {label}")

    if failed:
        print(f"\n{len(failed)}/{len(scenarios)} scenario(s) failed:", file=sys.stderr)
        for label in failed:
            print(f"  - {label}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
