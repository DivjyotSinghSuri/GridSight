"""Deterministic seeding utilities shared across all GridShield experiments.

Every scenario run derives all of its randomness (fault sampling, any
stochastic strategy behaviour) from a single master seed, so that a scenario
config plus a master seed is sufficient to exactly reproduce a run.
"""

import hashlib
import random


def derive_run_seed(master_seed: int, scenario_id: str, run_number: int) -> int:
    """Derive a reproducible per-repetition seed from a master seed.

    Combining the master seed with the scenario id and repetition number
    (rather than reusing the master seed directly) ensures different
    scenarios and different repetitions of the same scenario draw
    independent-looking but fully reproducible random sequences.

    Args:
        master_seed: the experiment-wide master seed.
        scenario_id: stable identifier of the scenario being run.
        run_number: zero-based repetition index within the scenario.

    Returns:
        int: a 32-bit deterministic seed derived from the inputs.
    """
    payload = f"{master_seed}:{scenario_id}:{run_number}".encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()
    return int(digest[:8], 16)


def seed_all(seed: int) -> None:
    """Seed every RNG GridShield or its dependencies may use.

    Seeds Python's ``random`` module unconditionally, and NumPy's global RNG
    if NumPy is importable. Safe to call even if NumPy is not installed.

    Args:
        seed: the seed to apply to all random number generators.
    """
    random.seed(seed)
    try:
        import numpy as np
    except ImportError:
        return
    np.random.seed(seed)
