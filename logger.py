"""
Centralized Logging Configuration
----------------------------------
Provides a single, consistent logger factory for every module
in the pipeline. All output flows through Python's built-in
logging framework instead of raw print() calls.

Usage:
    from logger import get_logger
    logger = get_logger(__name__)
"""

import logging
import os

# Directory where log files are stored
_LOG_DIR = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(_LOG_DIR, exist_ok=True)

# Shared formatter so every module looks the same
_FORMATTER = logging.Formatter(
    fmt='%(asctime)s | %(name)-18s | %(levelname)-8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)


def get_logger(name: str) -> logging.Logger:
    """Return a configured logger that writes to console AND file.

    Args:
        name: Module name (typically ``__name__``).

    Returns:
        A ``logging.Logger`` instance ready to use.
    """
    logger = logging.getLogger(name)

    # Avoid adding duplicate handlers on repeated calls
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)

        # --- Console handler (INFO and above) ---
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        console.setFormatter(_FORMATTER)

        # --- File handler (DEBUG and above, for full audit trail) ---
        file_handler = logging.FileHandler(
            os.path.join(_LOG_DIR, 'pipeline.log'),
            encoding='utf-8',
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(_FORMATTER)

        logger.addHandler(console)
        logger.addHandler(file_handler)

    return logger
