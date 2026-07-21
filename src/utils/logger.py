import logging
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parents[2] / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("GridSight")
logger.setLevel(logging.INFO)

# Prevent duplicate logs if imported multiple times
if not logger.handlers:
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s"
    )

    # Log to file
    file_handler = logging.FileHandler(LOG_DIR / "gridsight.log")
    file_handler.setFormatter(formatter)

    # Log to terminal
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
