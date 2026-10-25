"""Rich-powered logging for humans and agents."""

import logging

from rich.logging import RichHandler


def get_logger(name: str = "agentville", level: int = logging.INFO) -> logging.Logger:
    """Return a logger that writes through Rich to stderr."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.addHandler(RichHandler(show_path=False, rich_tracebacks=True))
    logger.setLevel(level)
    return logger
