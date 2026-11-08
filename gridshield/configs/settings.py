"""GridShield-wide constants: isolated storage paths, output layout, and defaults.

GridShield never writes to GridSight's ``database/gridsight.duckdb`` or its
real S3 bucket. All paths below point inside ``gridshield/outputs/``, which
is git-ignored and safe to delete/regenerate at any time.
"""

from gridshield.configs.paths import GRIDSHIELD_ROOT

OUTPUTS_DIR = GRIDSHIELD_ROOT / "outputs"
"""Root directory for all GridShield-generated artifacts."""

GRIDSHIELD_DB_PATH = OUTPUTS_DIR / "gridshield.duckdb"
"""GridShield's own isolated DuckDB file (never GridSight's production database)."""

BRONZE_SIM_DIR = OUTPUTS_DIR / "bronze_sim"
"""Local-filesystem stand-in for the real ``s3://gridsight-raw`` bronze bucket."""

CHECKPOINTS_DIR = OUTPUTS_DIR / "checkpoints"
"""Directory holding CheckpointStore state files for the checkpointing reliability strategy."""

EXPERIMENTS_OUTPUT_DIR = OUTPUTS_DIR
"""Base directory under which each experiment writes ``experiment_<n>/<scenario_id>/``."""

FIXTURES_DIR = GRIDSHIELD_ROOT / "fault_injection" / "fixtures"
"""Directory holding recorded response fixtures used to synthesize successful HTTP responses."""

CONFIGS_EXPERIMENTS_DIR = GRIDSHIELD_ROOT / "configs" / "experiments"
"""Directory holding the YAML scenario configs that drive the benchmark engine."""

VALIDATION_DBT_DIR = GRIDSHIELD_ROOT / "validation" / "dbt"
"""GridShield's own standalone dbt project used for dbt-based validation."""

DEFAULT_MASTER_SEED = 42
"""Default master random seed used when a scenario config does not specify one."""

DEFAULT_REPETITIONS = 15
"""Default number of repetitions per scenario, per the GridShield methodology."""

DEFAULT_KEEP_DAYS = 14
"""Default retention window (days) mirrored from GridSight's ``cleanup_old_files``."""


def ensure_output_dirs() -> None:
    """Create GridShield's isolated output directories if they do not already exist."""
    for directory in (OUTPUTS_DIR, BRONZE_SIM_DIR, CHECKPOINTS_DIR):
        directory.mkdir(parents=True, exist_ok=True)
