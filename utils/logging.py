import logging
from typing import Optional


class SimpleFormatter(logging.Formatter):
    """Custom formatter that only adds prefixes for warnings and errors."""

    def format(self, record: logging.LogRecord) -> str:
        if record.levelno >= logging.ERROR:
            return f"[ERROR] {record.getMessage()}"
        elif record.levelno >= logging.WARNING:
            return f"[WARN] {record.getMessage()}"
        return record.getMessage()


def get_screenplay_logger(name: str) -> logging.Logger:
    """
    Get a logger that will inherit from screenplay logger if it exists,
    otherwise just log to console.

    Args:
        name: Logger name/identifier

    Returns:
        Logger instance configured based on provided parameters
    """
    logger = logging.getLogger(f"screenplay.{name}")

    # Check if screenplay logger has any handlers configured
    screenplay_logger = logging.getLogger("screenplay")
    if not screenplay_logger.handlers:
        # Set up console logging if no handlers configured
        formatter = SimpleFormatter()
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        screenplay_logger.addHandler(console_handler)
        screenplay_logger.setLevel(logging.INFO)

    return logger


def setup_screenplay_logging(
    log_file: str, file_level: int = logging.DEBUG, console_level: int = logging.INFO
) -> None:
    """
    Set up root screenplay logger with both console and file output.
    This should be called at the start of the main script execution.

    Args:
        log_file: Path to log file for this execution
        file_level: Logging level for file output (default: INFO)
        console_level: Logging level for console output (default: INFO)
    """
    # Remove existing handlers from the entire logging hierarchy
    root = logging.getLogger()
    screenplay_logger = logging.getLogger("screenplay")
    for logger in [root, screenplay_logger]:
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

    # Create formatter and handlers
    formatter = SimpleFormatter()

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(console_level)

    # File handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    file_handler.setLevel(file_level)

    # Configure screenplay logger - set to lowest level to allow all messages through to handlers
    screenplay_logger.setLevel(logging.DEBUG)
    screenplay_logger.addHandler(console_handler)
    screenplay_logger.addHandler(file_handler)
    screenplay_logger.propagate = False  # Don't propagate to root logger

    # Reset all existing screenplay.* loggers to use the new configuration
    # pylint: disable=no-member
    existing_loggers = [
        name
        for name in logging.root.manager.loggerDict
        if name.startswith("screenplay.")
    ]
    # pylint: enable=no-member
    for name in existing_loggers:
        logger = logging.getLogger(name)
        # Remove any existing handlers
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        # Reset to use parent handlers
        logger.propagate = True
        logger.setLevel(logging.DEBUG)  # Allow all messages through to parent
