"""Shared result type for both Python and dbt validation checks."""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ValidationResult:
    """Outcome of a single validation check against a dataset.

    Attributes:
        check_name: stable identifier of the check that produced this result
            (e.g. ``"null_values"``, ``"duplicate_timestamps"``).
        source: which engine ran the check (``"python"`` or ``"dbt"``).
        passed: whether the check found no violations.
        violation_count: number of offending rows/values detected.
        message: human-readable summary, useful in logs and CSV output.
        details: optional extra structured context (e.g. offending values).
    """

    check_name: str
    source: str
    passed: bool
    violation_count: int = 0
    message: str = ""
    details: Optional[dict] = None


@dataclass
class ValidationReport:
    """Aggregates all :class:`ValidationResult`\\ s produced for one dataset/run.

    Attributes:
        results: the individual check outcomes.
    """

    results: List[ValidationResult] = field(default_factory=list)

    @property
    def all_passed(self) -> bool:
        """Whether every check in this report passed."""
        return all(r.passed for r in self.results)

    @property
    def violations_detected(self) -> int:
        """Total number of checks that failed (found at least one violation)."""
        return sum(1 for r in self.results if not r.passed)
