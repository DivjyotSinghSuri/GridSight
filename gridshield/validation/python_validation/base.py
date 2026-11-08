"""Abstract base class shared by every GridShield Python validation check."""

from abc import ABC, abstractmethod

import pandas as pd

from gridshield.validation.base import ValidationResult


class ValidationCheck(ABC):
    """Common interface for GridShield's Python validation checks.

    A check inspects a single DataFrame (typically the output of one of
    GridSight's unmodified ``fetch_*`` functions, before it is written to
    bronze storage) and reports whether it found any violations.
    """

    name: str = "base"
    """Short, stable identifier used in reports and output filenames."""

    @abstractmethod
    def run(self, df: pd.DataFrame) -> ValidationResult:
        """Run this check against ``df``.

        Args:
            df: the DataFrame to validate.

        Returns:
            ValidationResult: whether the check passed, and how many
            violations were found if not.
        """
        raise NotImplementedError
