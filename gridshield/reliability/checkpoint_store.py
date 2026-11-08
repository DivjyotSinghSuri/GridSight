"""Persistent checkpoint storage enabling interrupted ingestion work to resume safely."""

import json
from pathlib import Path
from typing import Optional

from gridshield.configs.settings import CHECKPOINTS_DIR


class CheckpointStore:
    """A JSON-file-backed key-value store for resumable unit-of-work state.

    Each scenario gets its own checkpoint file
    (``gridshield/outputs/checkpoints/<scenario_id>.json``) mapping a
    unit-of-work key (e.g. ``"weather:grid_04:2026-07-25"``) to a
    completion marker. If a benchmark run crashes mid-scenario, rerunning
    it lets :class:`~gridshield.reliability.checkpointing.CheckpointedBackoffStrategy`
    skip units of work already marked complete instead of redoing them.
    """

    def __init__(self, scenario_id: str, checkpoints_dir: Path = CHECKPOINTS_DIR):
        """Load (or initialize) the checkpoint file for a scenario.

        Args:
            scenario_id: stable identifier of the scenario this store tracks.
            checkpoints_dir: directory holding checkpoint JSON files.
        """
        self.scenario_id = scenario_id
        self._path = checkpoints_dir / f"{scenario_id}.json"
        self._state: dict = self._load()

    def _load(self) -> dict:
        """Load persisted state from disk, or return an empty dict if none exists yet."""
        if self._path.exists():
            with open(self._path) as f:
                return json.load(f)
        return {}

    def is_complete(self, key: str) -> bool:
        """Return whether the unit of work identified by ``key`` was already completed.

        Args:
            key: unit-of-work identifier.
        """
        return self._state.get(key, {}).get("complete", False)

    def mark_complete(self, key: str, metadata: Optional[dict] = None) -> None:
        """Record ``key`` as complete and flush immediately to disk.

        Flushing on every call (rather than batching) ensures a crash
        immediately after a successful unit of work still leaves that
        unit's completion durably recorded.

        Args:
            key: unit-of-work identifier.
            metadata: optional extra fields to store alongside the marker.
        """
        self._state[key] = {"complete": True, **(metadata or {})}
        self._flush()

    def clear(self) -> None:
        """Delete all checkpoint state for this scenario, forcing a fresh run from scratch."""
        self._state = {}
        if self._path.exists():
            self._path.unlink()

    def _flush(self) -> None:
        """Write the current in-memory state to disk, creating parent directories as needed."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "w") as f:
            json.dump(self._state, f, indent=2)
