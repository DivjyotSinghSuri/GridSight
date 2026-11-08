"""Regression tests guarding invariants the audit checked by hand: no duplicate
scenario ids, and equal retry budgets across the strategies Experiment 1 compares."""

from gridshield.benchmark.scenario import load_all_scenarios, load_scenarios_from_yaml
from gridshield.configs.settings import CONFIGS_EXPERIMENTS_DIR


def test_no_duplicate_scenario_ids_across_all_experiments():
    scenarios = load_all_scenarios(CONFIGS_EXPERIMENTS_DIR)
    ids = [(s.experiment_id, s.scenario_id) for s in scenarios]
    assert len(ids) == len(set(ids))
    # 92 original scenarios + 3 interrupt-and-resume scenarios (audit fix #4)
    assert len(scenarios) == 95


def test_interrupt_and_resume_scenarios_only_vary_reliability_strategy():
    scenarios = load_scenarios_from_yaml(CONFIGS_EXPERIMENTS_DIR / "experiment_1_reliability.yaml")
    interrupted = [s for s in scenarios if s.simulate_interruption_after_units is not None]
    assert len(interrupted) == 3
    assert {s.simulate_interruption_after_units for s in interrupted} == {3}
    assert {s.fault_probability for s in interrupted} == {0.0}
    assert {s.reliability_strategy for s in interrupted} == {
        "baseline", "exponential_backoff", "checkpointing"
    }


def test_experiment_1_holds_max_attempts_constant_across_retrying_strategies():
    scenarios = load_scenarios_from_yaml(CONFIGS_EXPERIMENTS_DIR / "experiment_1_reliability.yaml")
    max_attempts_by_strategy = {}
    for s in scenarios:
        if s.reliability_strategy == "baseline":
            continue
        max_attempts_by_strategy.setdefault(s.reliability_strategy, set()).add(
            s.reliability_params.get("max_attempts")
        )

    # every retrying strategy must use exactly one, and the SAME, max_attempts value —
    # otherwise a measured difference between strategies is confounded with retry budget.
    all_values = set()
    for strategy, values in max_attempts_by_strategy.items():
        assert len(values) == 1, f"{strategy} uses inconsistent max_attempts across its own scenarios: {values}"
        all_values |= values

    assert len(all_values) == 1, (
        f"retrying strategies use different max_attempts budgets: {max_attempts_by_strategy} "
        "— this confounds the strategy comparison"
    )
