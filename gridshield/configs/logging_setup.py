"""Per-scenario logging setup for GridShield experiments.

Mirrors GridSight's own ``src/utils/logger.py`` pattern (a named logger with
a file handler and a console handler) but creates one logger per scenario
run, writing detailed (DEBUG-level) logs into that scenario's own
``logs/`` directory in addition to the summary CSVs the benchmark engine
produces.
"""

import logging
from pathlib import Path


def get_scenario_logger(scenario_id: str, log_dir: Path) -> logging.Logger:
    """Build (or fetch) a logger dedicated to a single scenario run.

    Args:
        scenario_id: stable identifier of the scenario, used both as the
            logger name and to derive the log file name.
        log_dir: directory the log file should be written into; created if
            it does not already exist.

    Returns:
        logging.Logger: a logger named ``GridShield.<scenario_id>`` writing
        DEBUG-and-above records to ``<log_dir>/<scenario_id>.log`` and
        INFO-and-above records to the console.
    """
    log_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(f"GridShield.{scenario_id}")
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    if not logger.handlers:
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        )

        file_handler = logging.FileHandler(log_dir / f"{scenario_id}.log")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)

        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger
