"""Tests for GridShield's four reliability strategies and the checkpoint store."""

from gridshield.reliability.baseline import BaselineStrategy
from gridshield.reliability.checkpoint_store import CheckpointStore
from gridshield.reliability.checkpointing import CheckpointedBackoffStrategy
from gridshield.reliability.exponential_backoff import ExponentialBackoffStrategy
from gridshield.reliability.fixed_retry import FixedRetryStrategy


def _make_flaky(fail_times: int):
    """Build a callable that raises ``ValueError`` the first ``fail_times`` calls, then returns ``"ok"``."""
    calls = {"n": 0}

    def fn():
        calls["n"] += 1
        if calls["n"] <= fail_times:
            raise ValueError("boom")
        return "ok"

    return fn, calls


def test_baseline_does_not_retry():
    fn, calls = _make_flaky(fail_times=1)
    result = BaselineStrategy().execute(fn)
    assert result.success is False
    assert result.attempts == 1
    assert calls["n"] == 1


def test_baseline_succeeds_on_first_try():
    fn, _ = _make_flaky(fail_times=0)
    result = BaselineStrategy().execute(fn)
    assert result.success is True
    assert result.attempts == 1
    assert result.value == "ok"


def test_fixed_retry_recovers_within_max_attempts():
    fn, calls = _make_flaky(fail_times=2)
    result = FixedRetryStrategy(max_attempts=5, delay_seconds=0.001).execute(fn)
    assert result.success is True
    assert result.attempts == 3
    assert calls["n"] == 3


def test_fixed_retry_fails_after_exhausting_attempts():
    fn, calls = _make_flaky(fail_times=10)
    result = FixedRetryStrategy(max_attempts=3, delay_seconds=0.001).execute(fn)
    assert result.success is False
    assert result.attempts == 3
    assert calls["n"] == 3
    assert isinstance(result.error, ValueError)


def test_exponential_backoff_recovers():
    fn, _ = _make_flaky(fail_times=3)
    result = ExponentialBackoffStrategy(
        max_attempts=5, base_delay=0.001, max_delay=0.002
    ).execute(fn)
    assert result.success is True
    assert result.attempts == 4


def test_checkpointed_backoff_marks_and_skips_completed_work(tmp_path):
    store = CheckpointStore("test_scenario", checkpoints_dir=tmp_path)
    strategy = CheckpointedBackoffStrategy(store, max_attempts=5, base_delay=0.001, max_delay=0.002)

    fn, calls = _make_flaky(fail_times=1)
    first = strategy.execute(fn, checkpoint_key="unit1")
    assert first.success is True
    assert first.resumed_from_checkpoint is False
    assert calls["n"] == 2

    second = strategy.execute(fn, checkpoint_key="unit1")
    assert second.success is True
    assert second.resumed_from_checkpoint is True
    assert second.attempts == 0
    # The underlying callable must not be invoked again once checkpointed.
    assert calls["n"] == 2


def test_checkpoint_store_persists_across_instances(tmp_path):
    store = CheckpointStore("scenario_x", checkpoints_dir=tmp_path)
    assert store.is_complete("unit1") is False
    store.mark_complete("unit1")

    reloaded = CheckpointStore("scenario_x", checkpoints_dir=tmp_path)
    assert reloaded.is_complete("unit1") is True


def test_checkpoint_store_clear_resets_state(tmp_path):
    store = CheckpointStore("scenario_y", checkpoints_dir=tmp_path)
    store.mark_complete("unit1")
    store.clear()
    assert store.is_complete("unit1") is False
