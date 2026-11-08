"""Baseline reliability strategy: a single attempt, no retry."""

import time

from gridshield.reliability.base import ReliabilityStrategy
from gridshield.wrappers.base import WrapperResult


class BaselineStrategy(ReliabilityStrategy):
    """Executes the wrapped call exactly once; failures are never retried.

    Used as the control condition in Experiment 1 (Reliability benchmark)
    to measure how GridSight behaves with none of GridShield's added
    resilience layered on top.
    """

    name = "baseline"

    def execute(self, fn, checkpoint_key=None):
        """Run ``fn`` exactly once and report the outcome.

        Args:
            fn: zero-argument callable to execute.
            checkpoint_key: accepted for interface compatibility; unused.

        Returns:
            WrapperResult: ``attempts`` is always 1.
        """
        start = time.monotonic()
        try:
            value = fn()
            return WrapperResult(
                success=True,
                attempts=1,
                duration_seconds=time.monotonic() - start,
                value=value,
            )
        except Exception as e:
            return WrapperResult(
                success=False,
                attempts=1,
                duration_seconds=time.monotonic() - start,
                error=e,
            )
