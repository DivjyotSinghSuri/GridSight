"""Abstract base class shared by every GridShield reliability strategy."""

from abc import ABC, abstractmethod
from typing import Any, Callable, Optional

from gridshield.wrappers.base import WrapperResult


class ReliabilityStrategy(ABC):
    """Common interface for GridShield's reliability strategies.

    A strategy wraps a zero-argument callable (typically "fetch this source
    for this grid point/date and write it to bronze storage") and decides
    how many times to retry it, with what delay between attempts, and
    whether to persist progress via a checkpoint. Concrete strategies never
    modify the wrapped callable itself — they only control when and how
    often it is invoked.
    """

    name: str = "base"
    """Short, stable identifier used in scenario configs and output filenames."""

    @abstractmethod
    def execute(
        self, fn: Callable[[], Any], checkpoint_key: Optional[str] = None
    ) -> WrapperResult:
        """Run ``fn`` under this strategy's retry/backoff/checkpoint policy.

        Args:
            fn: a zero-argument callable performing one unit of ingestion work.
            checkpoint_key: stable identifier for this unit of work. Only
                strategies that support checkpointing use it; others ignore it.

        Returns:
            WrapperResult: the outcome, including attempt count and timing.
        """
        raise NotImplementedError
