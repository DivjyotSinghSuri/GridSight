"""Tests for Scenario and YAML scenario loading."""

import yaml

from gridshield.benchmark.scenario import Scenario, load_scenarios_from_yaml


def test_load_scenarios_merges_defaults_with_per_scenario_overrides(tmp_path):
    config = {
        "experiment_id": "test_experiment",
        "defaults": {"repetitions": 5, "master_seed": 1},
        "scenarios": [
            {"scenario_id": "a", "reliability_strategy": "baseline"},
            {"scenario_id": "b", "reliability_strategy": "fixed_retry", "repetitions": 10},
        ],
    }
    path = tmp_path / "test_experiment.yaml"
    path.write_text(yaml.dump(config))

    scenarios = load_scenarios_from_yaml(path)

    assert len(scenarios) == 2
    assert scenarios[0].repetitions == 5  # inherited from defaults
    assert scenarios[1].repetitions == 10  # overridden per-scenario
    assert all(s.experiment_id == "test_experiment" for s in scenarios)
    assert all(s.master_seed == 1 for s in scenarios)


def test_scenario_as_dict_round_trips_fields():
    scenario = Scenario(
        scenario_id="x", experiment_id="e", fault_type="http_500", fault_probability=0.2
    )
    as_dict = scenario.as_dict()
    assert as_dict["scenario_id"] == "x"
    assert as_dict["fault_type"] == "http_500"
    assert as_dict["fault_probability"] == 0.2
