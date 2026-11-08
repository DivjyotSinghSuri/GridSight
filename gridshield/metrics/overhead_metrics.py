"""Operational overhead metrics: runtime, storage, and (best-effort) memory."""

import tracemalloc
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class OverheadMetrics:
    """Operational overhead metrics for one run, used to compare baseline vs. GridShield-enabled pipelines.

    Attributes:
        runtime_seconds: wall-clock duration of the run. Callers (see
            ``benchmark/runner.py::_run_one_repetition``) time ingestion
            *and* validation together, so this reflects the full
            per-repetition cost, not ingestion alone.
        storage_bytes: total size, in bytes, of every file written under
            the measured output directory during the run.
        peak_memory_bytes: peak memory allocated during the run, measured
            via ``tracemalloc``; ``None`` if not measured. Covers the same
            ingestion+validation window as ``runtime_seconds``, but only
            the GridShield Python process — it cannot see the ``dbt``
            subprocess's memory (see README's Peak Memory caveat).
    """

    runtime_seconds: float
    storage_bytes: int
    peak_memory_bytes: Optional[int] = None


def measure_directory_size(path: Path) -> int:
    """Sum the size, in bytes, of every file under ``path``, recursively.

    Args:
        path: root directory to measure.

    Returns:
        int: total size in bytes; 0 if the directory does not exist.
    """
    if not path.exists():
        return 0
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


@contextmanager
def track_peak_memory():
    """Context manager measuring peak memory allocated (bytes) via ``tracemalloc`` during the block.

    Yields:
        dict: a mutable dict that gains the key ``"peak_bytes"`` once the
        ``with`` block exits.
    """
    tracemalloc.start()
    result: dict = {}
    try:
        yield result
    finally:
        _, peak = tracemalloc.get_traced_memory()
        result["peak_bytes"] = peak
        tracemalloc.stop()
