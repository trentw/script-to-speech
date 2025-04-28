"""Logging utility functions for the parser module."""

import logging
from pathlib import Path

from ...utils.logging import get_screenplay_logger, setup_screenplay_logging

logger = get_screenplay_logger("parser.utils.logging")


def setup_parser_logging(
    log_file: str, file_level: int = logging.DEBUG, console_level: int = logging.INFO
) -> None:
    """Set up logging for parser modules.

    Args:
        log_file: Path to log file
        file_level: Logging level for file output
        console_level: Logging level for console output
    """
    # Create log directory if it doesn't exist
    log_dir = Path(log_file).parent
    log_dir.mkdir(parents=True, exist_ok=True)

    # Set up logging
    setup_screenplay_logging(log_file, file_level, console_level)
    logger.debug(f"Logging set up with file: {log_file}")
