"""Tests that checkpointing genuinely resumes without redoing completed work after a
simulated interruption (audit Critical Issue #4), and that a non-checkpointing
strategy, by contrast, redoes everything — which is itself the point of comparison."""

from datetime import date

import pytest

from gridshield.fault_injection.injector import FaultInjector
from gridshield.reliability.checkpoint_store import CheckpointStore
from gridshield.reliability.checkpointing import CheckpointedBackoffStrategy
from gridshield.reliability.fixed_retry import FixedRetryStrategy
from gridshield.wrappers.ingestion_wrapper import run_ingestion_scenario

GRID_SUBSET = [("grid_01", 52.0, 10.0)]  # weather + irradiance = 2 units, plus daylight + generation = 4 total


def test_stop_after_units_truncates_the_pass(tmp_path):
    strategy = FixedRetryStrategy(max_attempts=1, delay_seconds=0.01)
    with FaultInjector(None, probability=0.0, seed=1) as injector:
        units = run_ingestion_scenario(
            strategy, date(2026, 7, 25), grid_points=GRID_SUBSET, bronze_root=tmp_path, stop_after_units=2
        )
    assert len(units) == 2
    assert injector.log.to_dict()["total_calls"] == 2


def test_checkpointing_resumes_without_refetching_completed_units(tmp_path):
    store = CheckpointStore("interrupt_test", checkpoints_dir=tmp_path / "checkpoints")
    strategy = CheckpointedBackoffStrategy(store, max_attempts=3, base_delay=0.01, max_delay=0.02)

    with FaultInjector(None, probability=0.0, seed=1) as injector:
        first_pass = run_ingestion_scenario(
            strategy, date(2026, 7, 25), grid_points=GRID_SUBSET, bronze_root=tmp_path, stop_after_units=2
        )
        assert len(first_pass) == 2
        calls_after_first_pass = injector.log.to_dict()["total_calls"]

        second_pass = run_ingestion_scenario(
            strategy, date(2026, 7, 25), grid_points=GRID_SUBSET, bronze_root=tmp_path
        )
        calls_after_second_pass = injector.log.to_dict()["total_calls"]

    assert len(second_pass) == 4  # weather, irradiance, daylight, generation
    resumed = [u for u in second_pass if u.result.resumed_from_checkpoint]
    freshly_fetched = [u for u in second_pass if not u.result.resumed_from_checkpoint]

    # the 2 units completed before the simulated crash must be resumed, not redone
    assert {u.source_hint for u in resumed} == {"weather", "irradiance"}
    assert all(u.result.attempts == 0 for u in resumed)
    # only the 2 units that were never attempted before the crash should make new calls
    assert {u.source_hint for u in freshly_fetched} == {"daylight", "generation"}
    assert calls_after_second_pass - calls_after_first_pass == 2


def test_non_checkpointing_strategy_redoes_everything_after_interruption(tmp_path):
    strategy = FixedRetryStrategy(max_attempts=3, delay_seconds=0.01)

    with FaultInjector(None, probability=0.0, seed=1) as injector:
        first_pass = run_ingestion_scenario(
            strategy, date(2026, 7, 25), grid_points=GRID_SUBSET, bronze_root=tmp_path, stop_after_units=2
        )
        assert len(first_pass) == 2
        calls_after_first_pass = injector.log.to_dict()["total_calls"]

        second_pass = run_ingestion_scenario(
            strategy, date(2026, 7, 25), grid_points=GRID_SUBSET, bronze_root=tmp_path
        )
        calls_after_second_pass = injector.log.to_dict()["total_calls"]

    assert len(second_pass) == 4
    # a strategy with no checkpoint store has no memory of the first pass at all:
    # the "resumed" pass refetches every single unit from scratch.
    assert all(not u.result.resumed_from_checkpoint for u in second_pass)
    assert calls_after_second_pass - calls_after_first_pass == 4
