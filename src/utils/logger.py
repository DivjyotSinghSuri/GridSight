import logging
import os

# Create logs directory if it doesn't exist
os.makedirs("logs", exist_ok=True)

logger = logging.getLogger("GridSight")

logger.setLevel(logging.INFO)

# Prevent duplicate logs if imported multiple times
if not logger.handlers:

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s"
    )

    # Log to file
    file_handler = logging.FileHandler("logs/gridsight.log")
    file_handler.setFormatter(formatter)

    # Log to terminal
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)