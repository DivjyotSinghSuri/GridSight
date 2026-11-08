"""Shared result type returned by every reliability strategy and wrapper call."""

from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class WrapperResult:
    """Outcome of one wrapped unit of work (a single fetch-and-store call).

    Attributes:
        success: whether the call ultimately succeeded.
        attempts: number of times the underlying callable was invoked.
        duration_seconds: total wall-clock time spent across all attempts,
            including any inter-attempt delays.
        value: the return value of the wrapped call, if it succeeded.
        error: the exception raised by the final failed attempt, if any.
        resumed_from_checkpoint: whether this call skipped work because a
            checkpoint indicated it had already completed in a prior,
            interrupted run.
    """

    success: bool
    attempts: int
    duration_seconds: float
    value: Any = None
    error: Optional[BaseException] = None
    resumed_from_checkpoint: bool = False
