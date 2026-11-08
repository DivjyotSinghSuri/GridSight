"""Fixed-interval retry reliability strategy."""

import time

from gridshield.reliability.base import ReliabilityStrategy
from gridshield.wrappers.base import WrapperResult


class FixedRetryStrategy(ReliabilityStrategy):
    """Retries the wrapped call up to ``max_attempts`` times with a fixed delay between attempts."""

    name = "fixed_retry"

    def __init__(self, max_attempts: int = 3, delay_seconds: float = 1.0):
        """Configure the fixed-retry policy.

        Args:
            max_attempts: maximum number of attempts, including the first.
            delay_seconds: fixed pause inserted between consecutive attempts.
        """
        self.max_attempts = max_attempts
        self.delay_seconds = delay_seconds

    def execute(self, fn, checkpoint_key=None):
        """Retry ``fn`` up to ``max_attempts`` times, pausing ``delay_seconds`` between attempts.

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
                    time.sleep(self.delay_seconds)
        return WrapperResult(
            success=False,
            attempts=self.max_attempts,
            duration_seconds=time.monotonic() - start,
            error=last_error,
        )
