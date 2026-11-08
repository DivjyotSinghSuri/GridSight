"""Runs a configured sequence of Python validation checks against a DataFrame."""

from typing import List

import pandas as pd

from gridshield.validation.base import ValidationReport
from gridshield.validation.python_validation.base import ValidationCheck


class PythonValidator:
    """Applies a configured list of :class:`ValidationCheck` instances to a DataFrame.

    Runs before transformation, directly on the output of GridSight's
    ``fetch_*`` functions.
    """

    def __init__(self, checks: List[ValidationCheck]):
        """Args:
        checks: the ordered list of checks to run.
        """
        self.checks = checks

    def validate(self, df: pd.DataFrame) -> ValidationReport:
        """Run every configured check against ``df``.

        Args:
            df: the DataFrame to validate.

        Returns:
            ValidationReport: one :class:`~gridshield.validation.base.ValidationResult`
            per configured check, in order.
        """
        return ValidationReport(results=[check.run(df) for check in self.checks])
