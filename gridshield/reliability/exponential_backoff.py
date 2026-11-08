"""Exponential backoff reliability strategy, with optional jitter."""

import random
import time

from gridshield.reliability.base import ReliabilityStrategy
from gridshield.wrappers.base import WrapperResult


class ExponentialBackoffStrategy(ReliabilityStrategy):
    """Retries the wrapped call with exponentially increasing delay between attempts.

    The delay before attempt N (N >= 2) is
    ``min(base_delay * 2**(N-2), max_delay)``, plus uniform jitter in
    ``[0, jitter_fraction * delay]`` to avoid synchronized retry storms.
    """

    name = "exponential_backoff"

    def __init__(
        self,
        max_attempts: int = 5,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        jitter_fraction: float = 0.1,
    ):
        """Configure the exponential backoff policy.

        Args:
            max_attempts: maximum number of attempts, including the first.
            base_delay: delay (seconds) before the second attempt.
            max_delay: upper bound on the delay between any two attempts.
            jitter_fraction: fraction of the computed delay added as
                uniform random jitter, in ``[0, 1]``.
        """
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.jitter_fraction = jitter_fraction

    def _delay_for(self, attempt: int) -> float:
        """Compute the backoff delay (seconds) before the given 1-based attempt number.

        Args:
            attempt: the attempt number the delay precedes (>= 2).

        Returns:
            float: delay in seconds, including jitter.
        """
        delay = min(self.base_delay * (2 ** (attempt - 2)), self.max_delay)
        jitter = random.uniform(0, self.jitter_fraction * delay)
        return delay + jitter

    def execute(self, fn, checkpoint_key=None):
        """Retry ``fn`` with exponential backoff up to ``max_attempts`` times.

        Args:
            fn: zero-argument callable to execute.
            checkpoint_key: accepted for interface compatibility; unused.

        Returns:
            WrapperResult: success as soon as one attempt succeeds, else
            failure after ``max_attempts`` exhausted attempts.
        """
        start = time.monotonic()
        last_error = None
        for attempt in range(1, self.max_attempts + 1):
            try:
                value = fn()
                return WrapperResult(
                    success=True,
                    attempts=attempt,
                    duration_seconds=time.monotonic() - start,
                    value=value,
                )
            except Exception as e:
                last_error = e
                if attempt < self.max_attempts:
                    time.sleep(self._delay_for(attempt + 1))
        return WrapperResult(
            success=False,
            attempts=self.max_attempts,
            duration_seconds=time.monotonic() - start,
            error=last_error,
        )
