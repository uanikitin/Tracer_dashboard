"""Logging configuration."""
import logging
import sys
from typing import Literal

from app.core.config import settings


def setup_logging(
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] | None = None
) -> logging.Logger:
    """Configure application logging."""
    if level is None:
        level = "DEBUG" if settings.debug else "INFO"

    # Root logger
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    # Reduce noise from libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("aiogram").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.debug else logging.WARNING
    )

    logger = logging.getLogger("tracer")
    logger.setLevel(level)
    return logger


logger = setup_logging()
