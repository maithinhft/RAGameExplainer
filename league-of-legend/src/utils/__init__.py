"""Structured logging setup using the Rich library."""

from __future__ import annotations

import logging
import sys

from rich.console import Console
from rich.logging import RichHandler

_console = Console(stderr=True)


def setup_logger(name: str = "lol_crawler", level: str = "INFO") -> logging.Logger:
    """Create and return a configured logger instance.

    Args:
        name: Logger name, used as prefix for log messages.
        level: Logging level string (DEBUG, INFO, WARNING, ERROR, CRITICAL).

    Returns:
        Configured ``logging.Logger`` instance.
    """
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(numeric_level)

    handler = RichHandler(
        console=_console,
        show_time=True,
        show_path=False,
        markup=True,
        rich_tracebacks=True,
        tracebacks_show_locals=False,
    )
    handler.setLevel(numeric_level)

    fmt = logging.Formatter("%(message)s", datefmt="[%X]")
    handler.setFormatter(fmt)

    logger.addHandler(handler)
    logger.propagate = False

    return logger


def get_logger(name: str | None = None) -> logging.Logger:
    """Return the child logger for the given module name.

    Args:
        name: Dot-separated child name (e.g. ``crawlers.champion``).
              If *None*, returns the root crawler logger.
    """
    base = "lol_crawler"
    if name:
        return logging.getLogger(f"{base}.{name}")
    return logging.getLogger(base)
