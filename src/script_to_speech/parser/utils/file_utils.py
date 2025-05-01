"""File utility functions for the parser module."""

import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Tuple

from ...utils.logging import get_screenplay_logger

logger = get_screenplay_logger("parser.utils.file")


def get_project_root() -> Path:
    """Get the project root directory.

    Returns:
        Path to project root directory
    """
    return Path(__file__).resolve().parent.parent.parent.parent.parent


def sanitize_name(name: str) -> str:
    """Sanitize a name for use in filenames and directories.

    Args:
        name: Original name

    Returns:
        Sanitized name with special characters removed
    """
    sanitized = re.sub(r"[^\w\s-]", "", name)
    sanitized = re.sub(r"[-\s]+", "_", sanitized)
    sanitized = sanitized.strip("_")
    return sanitized


def create_directory_structure() -> None:
    """Create the necessary directory structure relative to project root."""
    root = get_project_root()
    required_dirs = [root / "input", root / "output" / "parser_logs"]

    for dir_path in required_dirs:
        dir_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Ensured directory exists: {dir_path}")


def create_output_folders(screenplay_name: str, run_mode: str = "") -> Tuple[str, str]:
    """Create and return paths for output folders.

    Args:
        screenplay_name: Name of the screenplay
        run_mode: String indicating run mode for log file name prefix

    Returns:
        Tuple of (screenplay_directory, log_file)
    """
    root = get_project_root()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    screenplay_dir = root / "input" / screenplay_name
    screenplay_dir.mkdir(parents=True, exist_ok=True)

    mode_prefix = f"[{run_mode}]_" if run_mode else ""
    log_file = (
        root
        / "output"
        / "parser_logs"
        / f"{mode_prefix}{screenplay_name}_{timestamp}.log"
    )

    return str(screenplay_dir), str(log_file)
