"""Backoff-with-checkpointing reliability strategy."""

from gridshield.reliability.base import ReliabilityStrategy
from gridshield.reliability.checkpoint_store import CheckpointStore
from gridshield.reliability.exponential_backoff import ExponentialBackoffStrategy
from gridshield.wrappers.base import WrapperResult


class CheckpointedBackoffStrategy(ReliabilityStrategy):
    """Composes exponential backoff with a :class:`CheckpointStore` so interrupted runs resume safely.

    Before running a unit of work, checks whether ``checkpoint_key`` was
    already marked complete by a prior (possibly crashed) run of the same
    scenario; if so, the unit of work is skipped entirely. On success, the
    key is marked complete so a future rerun can skip it too.
    """

    name = "checkpointing"

    def __init__(
        self,
        checkpoint_store: CheckpointStore,
        max_attempts: int = 5,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        jitter_fraction: float = 0.1,
    ):
        """Configure the checkpointed backoff policy.

        Args:
            checkpoint_store: the store tracking completed units of work
                for the current scenario.
            max_attempts: maximum attempts per unit of work, including the first.
            base_delay: delay (seconds) before the second attempt.
            max_delay: upper bound on the delay between any two attempts.
            jitter_fraction: fraction of the computed delay added as jitter.
        """
        self.checkpoint_store = checkpoint_store
        self._backoff = ExponentialBackoffStrategy(
            max_attempts=max_attempts,
            base_delay=base_delay,
            max_delay=max_delay,
            jitter_fraction=jitter_fraction,
        )

    def execute(self, fn, checkpoint_key=None):
        """Skip ``fn`` if already checkpointed complete; otherwise run it under exponential backoff.

        Args:
            fn: zero-argument callable to execute.
            checkpoint_key: unit-of-work identifier used to check for and
                record completion. If ``None``, behaves exactly like
                :class:`~gridshield.reliability.exponential_backoff.ExponentialBackoffStrategy`
                with no checkpointing.

        Returns:
            WrapperResult: ``resumed_from_checkpoint=True`` and
            ``attempts=0`` if the unit of work was already complete;
            otherwise the outcome of running ``fn`` under backoff, with the
            key marked complete on success.
        """
        if checkpoint_key and self.checkpoint_store.is_complete(checkpoint_key):
            return WrapperResult(
                success=True,
                attempts=0,
                duration_seconds=0.0,
                resumed_from_checkpoint=True,
            )

        result = self._backoff.execute(fn)

        if result.success and checkpoint_key:
            self.checkpoint_store.mark_complete(checkpoint_key)

        return result
