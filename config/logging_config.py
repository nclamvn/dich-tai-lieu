"""
Centralized logging configuration.
Replace all print() with proper logger.
"""
import logging
import logging.handlers
from pathlib import Path
from .constants import (
    LOG_LEVEL, LOG_FORMAT, LOG_FILE,
    LOG_MAX_SIZE_MB, LOG_BACKUP_COUNT
)


def setup_logger(name: str = None) -> logging.Logger:
    """
    Get or create a configured logger.

    Usage:
        from config.logging_config import setup_logger
        logger = setup_logger(__name__)
        logger.info("Message here")

    Args:
        name: Logger name. If None, uses 'translator'.

    Returns:
        Configured logging.Logger instance.
    """
    logger = logging.getLogger(name or 'translator')

    # Avoid adding handlers multiple times
    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, LOG_LEVEL))

    # Console handler - INFO level
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter(LOG_FORMAT))
    logger.addHandler(console)

    # File handler with rotation - DEBUG level
    log_path = Path(LOG_FILE)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILE,
        maxBytes=LOG_MAX_SIZE_MB * 1024 * 1024,
        backupCount=LOG_BACKUP_COUNT
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    logger.addHandler(file_handler)

    return logger


def get_logger(name: str = None) -> logging.Logger:
    """
    Alias for setup_logger for convenience.

    Usage:
        from config.logging_config import get_logger
        logger = get_logger(__name__)
    """
    return setup_logger(name)


# Singleton logger for quick imports
# Usage: from config.logging_config import logger
logger = setup_logger('translator')
