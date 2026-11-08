"""Resolves the GridSight repository root and GridShield's own root.

Mirrors the root-discovery pattern used by ``dags/gridsight_pipeline.py``
(GRIDSIGHT_PROJECT_ROOT env var, falling back to walking up from this file
looking for ``config.py`` + ``src/``), so GridShield locates the same
repository root whether invoked from the repo root, from within
``gridshield/``, or from Airflow.
"""

import os
import sys
from pathlib import Path


def resolve_gridsight_root() -> Path:
    """Locate the GridSight repository root.

    Checks the ``GRIDSIGHT_PROJECT_ROOT`` environment variable first, then
    walks up from this file's directory and the current working directory
    looking for a directory containing both ``config.py`` and ``src/``.

    Returns:
        Path: absolute path to the GridSight repository root.

    Raises:
        RuntimeError: if no such directory can be found.
    """
    env_root = os.environ.get("GRIDSIGHT_PROJECT_ROOT")
    if env_root:
        return Path(env_root).expanduser().resolve()

    candidate_starts = [Path(__file__).resolve().parent, Path.cwd().resolve()]

    for start_path in candidate_starts:
        for candidate in [start_path] + list(start_path.parents):
            if (candidate / "config.py").is_file() and (candidate / "src").is_dir():
                return candidate

    raise RuntimeError(
        "Could not locate the GridSight project root. "
        "Set GRIDSIGHT_PROJECT_ROOT to the repository root."
    )


GRIDSIGHT_ROOT: Path = resolve_gridsight_root()
"""Absolute path to the GridSight repository root."""

GRIDSHIELD_ROOT: Path = Path(__file__).resolve().parents[1]
"""Absolute path to the gridshield/ package root."""

if str(GRIDSIGHT_ROOT) not in sys.path:
    sys.path.insert(0, str(GRIDSIGHT_ROOT))
