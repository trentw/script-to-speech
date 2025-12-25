"""File system utility functions for the script_to_speech package."""

import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

from pathvalidate import sanitize_filename

from .logging import get_screenplay_logger

logger = get_screenplay_logger("utils.file_system")


class PathSecurityValidator:
    """Secure path validation and construction to prevent directory traversal attacks."""

    def __init__(self, base_path: Path):
        """Initialize the validator with a base path.

        Args:
            base_path: The base directory that all constructed paths must be within
        """
        self.base_path = base_path.resolve()
        logger.debug(
            f"PathSecurityValidator initialized with base_path: {self.base_path}"
        )

    def validate_and_join(self, *path_parts: str) -> Path:
        """Safely join path parts with the base path, preventing directory traversal.

        Args:
            *path_parts: Path components to join

        Returns:
            A secure Path object within the base path

        Raises:
            ValueError: If the resulting path would be outside the base path
        """
        # Sanitize each path part using pathvalidate
        safe_parts = []
        for part in path_parts:
            if part:  # Skip empty parts
                safe_part = sanitize_filename(part)
                safe_parts.append(safe_part)

        if not safe_parts:
            return self.base_path

        # Join with base path and resolve to canonical form
        full_path = self.base_path.joinpath(*safe_parts).resolve()

        # Security validation: ensure the resolved path is within base_path
        if self.base_path not in full_path.parents and full_path != self.base_path:
            raise ValueError(
                f"Invalid path destination: {'/'.join(path_parts)} resolves outside base path"
            )

        logger.debug(f"Validated path: {full_path}")
        return full_path

    def validate_existing_path(self, path: Path) -> Path:
        """Validate that an existing path is within the base path.

        Args:
            path: Path to validate

        Returns:
            The validated path

        Raises:
            ValueError: If the path is outside the base path
        """
        resolved_path = path.resolve()

        if (
            self.base_path not in resolved_path.parents
            and resolved_path != self.base_path
        ):
            raise ValueError(f"Path {path} is outside the allowed base path")

        return resolved_path


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
    input_file_path_str: str,
    run_mode: str = "",
    dummy_provider_override: bool = False,
    base_path: Optional[Path] = None,
) -> Tuple[
    Path, Path, Path, Path
]:  # main_output_folder, cache_folder, logs_folder, log_file_full_path
    """
    Creates and returns paths for standardized output folders and the log file.

    Args:
        input_file_path_str: Path to the input screenplay file (string).
        run_mode: String indicating the run mode (e.g., "dry-run", "populate-cache") for log file naming.
        dummy_provider_override: If True, modifies cache folder name and log file prefix.
        base_path: Base directory for all operations. If None, uses current working directory.

    Returns:
        A tuple containing Path objects:
        (main_output_folder, cache_folder, logs_folder, log_file_full_path)
    """
    # Auto-detect base path if not provided (backward compatibility)
    if base_path is None:
        base_path = Path.cwd().resolve()

    # Initialize security validator
    validator = PathSecurityValidator(base_path)

    input_file_path_obj = Path(input_file_path_str)
    # base_name will be like "my_screenplay" from "input/my_screenplay.pdf"
    base_name = input_file_path_obj.stem
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Use security validator for all path construction
    main_output_folder = validator.validate_and_join("output", base_name)

    cache_folder_name = "cache"
    if dummy_provider_override:
        cache_folder_name = f"dummy_{cache_folder_name}"
    cache_folder = validator.validate_and_join("output", base_name, cache_folder_name)

    logs_folder = validator.validate_and_join("output", base_name, "logs")

    # Standardized log file naming
    dummy_prefix_str = "[dummy]" if dummy_provider_override else ""
    mode_prefix_str = f"[{run_mode}]_" if run_mode else ""
    log_file_name = f"{dummy_prefix_str}{mode_prefix_str}log_{timestamp}.txt"
    log_file_full_path = validator.validate_and_join(
        "output", base_name, "logs", log_file_name
    )

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
