"""Scenario definition and YAML loading for GridShield's benchmark engine.

A :class:`Scenario` is a single point in the configuration space the
GridShield methodology explores: a reliability strategy, a validation
strategy, a fault type/probability, and a repetition count. The benchmark
engine never hardcodes scenarios — they are always loaded from YAML files
under ``gridshield/configs/experiments/``.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from gridshield.configs.settings import DEFAULT_MASTER_SEED, DEFAULT_REPETITIONS


@dataclass
class Scenario:
    """One fully-specified benchmark configuration.

    Attributes:
        scenario_id: stable, filesystem-safe identifier for this scenario,
            unique within its experiment.
        experiment_id: which experiment this scenario belongs to (e.g.
            ``"experiment_1_reliability"``); also the name of its output subfolder.
        reliability_strategy: ``"baseline"``, ``"fixed_retry"``,
            ``"exponential_backoff"``, or ``"checkpointing"``.
        validation_strategy: ``"none"``, ``"python"``, ``"dbt"``, or ``"combined"``.
        fault_type: one of the :class:`~gridshield.fault_injection.faults.Fault`
            values, or ``"none"``/``None`` for no fault injection.
        fault_probability: probability (0.0-1.0) that a given HTTP call is faulted.
        repetitions: number of repetitions to run for this scenario.
        master_seed: master seed all per-repetition seeds derive from.
        grid_points_limit: number of grid points sampled per repetition;
            keeps 15-repetition runs tractable given GridSight's built-in
            per-call courtesy sleep. ``None`` uses the full 25-point grid.
        run_date: the ingestion date to fetch, as ``YYYY-MM-DD``; defaults
            to the date GridShield's recorded fixtures represent.
        reliability_params: extra keyword arguments passed to the
            reliability strategy's constructor.
        validation_params: extra keyword arguments controlling validation,
            e.g. ``{"inject_violation": "null_values"}``.
        simulate_interruption_after_units: if set, the runner simulates a
            process crash after this many ingestion units of work in the
            first of two passes, then reruns the full pass with the same
            reliability strategy/checkpoint store — demonstrating whether
            the strategy actually resumes without redoing completed work
            (only ``"checkpointing"`` does; other strategies redo
            everything, which is itself the point of comparison).
            ``None`` (the default) runs a single, uninterrupted pass.
    """

    scenario_id: str
    experiment_id: str
    reliability_strategy: str = "baseline"
    validation_strategy: str = "none"
    fault_type: Optional[str] = None
    fault_probability: float = 0.0
    repetitions: int = DEFAULT_REPETITIONS
    master_seed: int = DEFAULT_MASTER_SEED
    grid_points_limit: Optional[int] = 3
    run_date: str = "2026-07-25"
    reliability_params: Dict[str, Any] = field(default_factory=dict)
    validation_params: Dict[str, Any] = field(default_factory=dict)
    simulate_interruption_after_units: Optional[int] = None

    def as_dict(self) -> Dict[str, Any]:
        """Serialize this scenario to a plain dict, for ``config.json``/``metadata.json``."""
        return {
            "scenario_id": self.scenario_id,
            "experiment_id": self.experiment_id,
            "reliability_strategy": self.reliability_strategy,
            "validation_strategy": self.validation_strategy,
            "fault_type": self.fault_type,
            "fault_probability": self.fault_probability,
            "repetitions": self.repetitions,
            "master_seed": self.master_seed,
            "grid_points_limit": self.grid_points_limit,
            "run_date": self.run_date,
            "reliability_params": self.reliability_params,
            "validation_params": self.validation_params,
            "simulate_interruption_after_units": self.simulate_interruption_after_units,
        }


def load_scenarios_from_yaml(path: Path) -> List[Scenario]:
    """Load every scenario defined in one experiment YAML config file.

    The file must have an ``experiment_id`` key, an optional ``defaults``
    mapping applied to every scenario before its own fields override it,
    and a ``scenarios`` list of per-scenario overrides.

    Args:
        path: path to a YAML file under ``gridshield/configs/experiments/``.

    Returns:
        list[Scenario]: one :class:`Scenario` per entry in the file's
        ``scenarios`` list, in file order.
    """
    with open(path) as f:
        raw = yaml.safe_load(f)

    experiment_id = raw["experiment_id"]
    defaults = raw.get("defaults", {})

    scenarios = []
    for entry in raw["scenarios"]:
        merged = {**defaults, **entry}
        scenarios.append(Scenario(experiment_id=experiment_id, **merged))
    return scenarios


def load_all_scenarios(experiments_dir: Path) -> List[Scenario]:
    """Load scenarios from every experiment YAML file in a directory.

    Args:
        experiments_dir: directory containing one YAML file per experiment.

    Returns:
        list[Scenario]: all scenarios across all experiment files, sorted
        by filename for a stable, reproducible ordering.
    """
    scenarios: List[Scenario] = []
    for yaml_path in sorted(experiments_dir.glob("*.yaml")):
        scenarios.extend(load_scenarios_from_yaml(yaml_path))
    return scenarios
