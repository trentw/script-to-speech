"""File system utility functions for the script_to_speech package."""

import os
import re
from datetime import datetime
from pathlib import Path
from typing import Tuple

from .logging import get_screenplay_logger

logger = get_screenplay_logger("utils.file_system")


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


def create_output_folders(
    input_file_path_str: str, run_mode: str = "", dummy_provider_override: bool = False
) -> Tuple[
    Path, Path, Path, Path
]:  # main_output_folder, cache_folder, logs_folder, log_file_full_path
    """
    Creates and returns paths for standardized output folders and the log file.

    Args:
        input_file_path_str: Path to the input screenplay file (string).
        run_mode: String indicating the run mode (e.g., "dry-run", "populate-cache") for log file naming.
        dummy_provider_override: If True, modifies cache folder name and log file prefix.

    Returns:
        A tuple containing Path objects:
        (main_output_folder, cache_folder, logs_folder, log_file_full_path)
    """
    input_file_path_obj = Path(input_file_path_str)
    # base_name will be like "my_screenplay" from "input/my_screenplay.pdf"
    base_name = input_file_path_obj.stem
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # All paths are relative to the project root where 'output/' will reside.
    # Path("output") assumes the script is run from the project root.
    main_output_folder = Path("output") / base_name

    cache_folder_name = "cache"
    if dummy_provider_override:
        cache_folder_name = f"dummy_{cache_folder_name}"
    cache_folder = main_output_folder / cache_folder_name

    logs_folder = main_output_folder / "logs"

    # Standardized log file naming
    dummy_prefix_str = "[dummy]" if dummy_provider_override else ""
    mode_prefix_str = f"[{run_mode}]_" if run_mode else ""
    log_file_name = f"{dummy_prefix_str}{mode_prefix_str}log_{timestamp}.txt"
    log_file_full_path = logs_folder / log_file_name

    # Create directories. Ensure parent directories are created.
    # It's good practice to create the main_output_folder first if others are subdirectories,
    # though mkdir(parents=True) handles nested creation.
    main_output_folder.mkdir(parents=True, exist_ok=True)
    cache_folder.mkdir(parents=True, exist_ok=True)
    logs_folder.mkdir(parents=True, exist_ok=True)

    logger.debug(f"Ensured main output folder: {main_output_folder.resolve()}")
    logger.debug(f"Ensured cache folder: {cache_folder.resolve()}")
    logger.debug(f"Ensured logs folder: {logs_folder.resolve()}")
    logger.debug(f"Log file path determined: {log_file_full_path.resolve()}")

    return main_output_folder, cache_folder, logs_folder, log_file_full_path
