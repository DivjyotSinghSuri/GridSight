"""Subprocess wrapper around the ``dbt`` CLI for GridShield's standalone validation dbt project.

Shells out to ``dbt`` (already a GridSight dependency via ``dbt-duckdb``)
rather than importing dbt's Python API, keeping this wrapper decoupled from
dbt's internal library surface — the same approach
``dags/gridsight_pipeline.py`` takes with its ``BashOperator`` dbt step.
Always targets ``gridshield/validation/dbt/`` and GridShield's isolated
DuckDB file; never ``gridsight_dbt/`` or the production database.
"""

import json
import os
import subprocess
from pathlib import Path
from typing import Dict, List

from gridshield.configs.settings import GRIDSHIELD_DB_PATH, VALIDATION_DBT_DIR
from gridshield.validation.base import ValidationResult

DBT_TEST_MACRO_TO_CHECK_NAME: Dict[str, str] = {
    "not_null": "null_values",
    "no_duplicate_timestamps": "duplicate_timestamps",
    "min_row_count": "missing_rows",
    "expected_columns": "schema_mismatch",
    "accepted_range": "invalid_numeric_range",
    "column_type": "wrong_datatype",
    "no_future_timestamps": "future_timestamps",
    "freshness": "freshness_violation",
}
"""Maps each dbt generic-test macro name to GridShield's canonical check-name vocabulary.

``run_results.json``'s own ``unique_id`` is not usable as a check name: for
tests whose full name is long (most of this project's, since generated
names embed model + column + params), dbt truncates it to an opaque hash
(e.g. ``"26b1aeef68"``), and even when it isn't hashed the full name never
matches the clean vocabulary Python's ``ValidationCheck.name`` values use
(e.g. ``"not_null_stg_weather_timestamp"`` vs. ``"null_values"``). The
macro name in ``manifest.json``'s ``test_metadata.name`` is stable and
keyed by the same ``unique_id`` regardless of hashing, so it is the
reliable source for the canonical name instead.
"""


class DbtValidationWrapper:
    """Runs GridShield's standalone dbt validation project against the isolated DuckDB file."""

    def __init__(self, project_dir: Path = VALIDATION_DBT_DIR, db_path: Path = GRIDSHIELD_DB_PATH):
        """Configure the wrapper.

        Args:
            project_dir: path to GridShield's standalone dbt project.
            db_path: path to GridShield's isolated DuckDB file.
        """
        self.project_dir = project_dir
        self.db_path = db_path

    def _env(self) -> dict:
        """Build the environment ``dbt`` subprocess calls run under.

        Sets ``GRIDSHIELD_DB_PATH`` (read by ``profiles.yml`` via
        ``env_var()``) and ``DBT_PROFILES_DIR`` (so dbt finds this
        project's ``profiles.yml`` instead of ``~/.dbt/``).
        """
        env = os.environ.copy()
        env["GRIDSHIELD_DB_PATH"] = str(self.db_path)
        env["DBT_PROFILES_DIR"] = str(self.project_dir)
        return env

    def _run_dbt(self, *args: str) -> subprocess.CompletedProcess:
        """Invoke ``dbt <args>`` against this project.

        Args:
            *args: dbt subcommand and flags, e.g. ``"run"`` or ``"test"``.

        Returns:
            subprocess.CompletedProcess: the completed invocation, with
            captured stdout/stderr.
        """
        return subprocess.run(
            ["dbt", *args, "--profiles-dir", str(self.project_dir), "--project-dir", str(self.project_dir)],
            cwd=self.project_dir,
            env=self._env(),
            capture_output=True,
            text=True,
        )

    def run_models(self) -> subprocess.CompletedProcess:
        """Run ``dbt run`` to (re)build the staging models from GridShield's isolated bronze tables.

        Returns:
            subprocess.CompletedProcess: the completed ``dbt run`` invocation.

        Raises:
            RuntimeError: if ``dbt run`` exits non-zero. A failed ``dbt run``
                (bad SQL, a missing source table, etc.) must not be allowed
                to pass silently, since ``run_tests()`` would otherwise
                evaluate stale or partially-built models without any
                indication the underlying build failed.
        """
        result = self._run_dbt("run")
        if result.returncode != 0:
            raise RuntimeError(
                f"dbt run failed (exit code {result.returncode}) in {self.project_dir}:\n"
                f"{result.stdout}\n{result.stderr}"
            )
        return result

    def _load_test_macro_names(self) -> Dict[str, str]:
        """Map each test's ``unique_id`` to its generic-test macro name via ``target/manifest.json``.

        Returns:
            dict[str, str]: ``unique_id`` -> macro name (e.g. ``"not_null"``,
            ``"accepted_range"``); empty if the manifest is missing.
        """
        manifest_path = self.project_dir / "target" / "manifest.json"
        if not manifest_path.exists():
            return {}
        with open(manifest_path) as f:
            manifest = json.load(f)
        macro_names = {}
        for unique_id, node in manifest.get("nodes", {}).items():
            test_metadata = node.get("test_metadata")
            if test_metadata:
                macro_names[unique_id] = test_metadata["name"]
        return macro_names

    def run_tests(self) -> List[ValidationResult]:
        """Run ``dbt test`` and translate ``target/run_results.json`` into :class:`ValidationResult`\\ s.

        Each result's ``check_name`` is GridShield's canonical check-name
        (e.g. ``"null_values"``), resolved via ``manifest.json``'s
        ``test_metadata.name`` and :data:`DBT_TEST_MACRO_TO_CHECK_NAME` —
        not derived from ``unique_id``, which dbt truncates to an opaque
        hash for any test whose generated name is long. A test whose macro
        isn't in the mapping (e.g. dbt's built-in ``unique``, unused by
        this project today) falls back to its raw macro name so it still
        contributes an interpretable, if unmapped, result.

        Tests with status ``"skipped"`` (e.g. because an upstream model
        failed to build) carry no evidence either way and are excluded
        from the returned list entirely, rather than being counted as a
        detected violation.

        Returns:
            list[ValidationResult]: one entry per non-skipped dbt test
            executed; empty if ``dbt test`` produced no results file (e.g.
            it crashed before writing one).
        """
        self._run_dbt("test")

        results_path = self.project_dir / "target" / "run_results.json"
        if not results_path.exists():
            return []

        with open(results_path) as f:
            run_results = json.load(f)
        macro_names = self._load_test_macro_names()

        validation_results = []
        for result in run_results.get("results", []):
            status = result["status"]
            if status == "skipped":
                continue

            unique_id = result["unique_id"]
            macro_name = macro_names.get(unique_id, unique_id.split(".")[-1])
            check_name = DBT_TEST_MACRO_TO_CHECK_NAME.get(macro_name, macro_name)

            passed = status == "pass"
            failures = result.get("failures")
            validation_results.append(
                ValidationResult(
                    check_name=check_name,
                    source="dbt",
                    passed=passed,
                    violation_count=failures if failures is not None else (0 if passed else 1),
                    message=f"[{status}] {result.get('message') or status}",
                )
            )
        return validation_results
