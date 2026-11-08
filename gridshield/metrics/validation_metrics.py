"""Validation-layer metrics: detection rate, false positives, propagation."""

from dataclasses import dataclass
from typing import Set

from gridshield.validation.base import ValidationReport


@dataclass
class ValidationMetrics:
    """Aggregate validation-layer metrics for one scenario repetition.

    Attributes:
        detection_rate: fraction of known/injected data-quality violations
            that the validator's checks flagged.
        false_positive_rate: fraction of the validator's failed checks that
            did not correspond to an actual injected violation.
        propagation: count of known/injected violations the validator
            failed to flag, i.e. that would propagate downstream undetected.
        total_checks_run: number of validation checks executed.
        checks_failed: number of validation checks that failed.
    """

    detection_rate: float
    false_positive_rate: float
    propagation: int
    total_checks_run: int
    checks_failed: int


def compute_validation_metrics(
    report: ValidationReport,
    injected_violation_check_names: Set[str],
) -> ValidationMetrics:
    """Compute detection rate, false positive rate, and propagation for one validation report.

    Matches failed checks against a ground-truth set of check names that
    correspond to data-quality issues GridShield deliberately injected into
    the input for this repetition.

    Args:
        report: the report produced by ``PythonValidator.validate()`` and/or
            ``DbtValidationWrapper.run_tests()`` (results from both may be
            combined into one report for the "combined" validation strategy).
        injected_violation_check_names: check names expected to fail because
            a corresponding violation was deliberately injected.

    Returns:
        ValidationMetrics.
    """
    failed_checks = {r.check_name for r in report.results if not r.passed}
    detected = failed_checks & injected_violation_check_names
    false_positives = failed_checks - injected_violation_check_names
    missed = injected_violation_check_names - failed_checks

    detection_rate = (
        len(detected) / len(injected_violation_check_names)
        if injected_violation_check_names
        else 1.0
    )
    false_positive_rate = len(false_positives) / len(failed_checks) if failed_checks else 0.0

    return ValidationMetrics(
        detection_rate=detection_rate,
        false_positive_rate=false_positive_rate,
        propagation=len(missed),
        total_checks_run=len(report.results),
        checks_failed=len(failed_checks),
    )
