"""
Utility module for loading environment variables from .env files.
"""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from script_to_speech.utils.logging import get_screenplay_logger

# Define logger for this module
logger = get_screenplay_logger("utils.env_utils")


def load_environment_variables(
    verbose: bool = True, workspace_dir: Optional[Path] = None
) -> bool:
    """
    Load environment variables from a .env file in the workspace directory.

    This function looks for a .env file in the workspace directory and loads
    any environment variables defined in it. It's primarily used to load API
    keys for TTS providers.

    The workspace directory is determined by:
    - If workspace_dir is provided, use that
    - Otherwise, use get_default_workspace_dir() which handles dev/prod modes:
      - Dev mode: project root (where pyproject.toml is located)
      - Prod mode: Application Support directory

    Args:
        verbose: Whether to log information about the .env file loading
        workspace_dir: Optional workspace directory path. If None, uses
                      get_default_workspace_dir() for dev/prod detection.

    Returns:
        bool: True if a .env file was found and loaded, False otherwise
    """
    # Determine workspace directory
    if workspace_dir is None:
        # Avoid circular import by importing here
        try:
            from script_to_speech.gui_backend.config import (
                get_default_workspace_dir,
            )

            workspace_dir = get_default_workspace_dir()
        except ImportError:
            # Fallback to project root if gui_backend not available (e.g., CLI usage)
            import sys

            if getattr(sys, "frozen", False):
                # In PyInstaller, __file__ path traversal doesn't work
                # If import fails in production, it's a build error - fail loudly
                raise ImportError(
                    "Cannot import get_default_workspace_dir in frozen executable. "
                    "This indicates a build or packaging error."
                )
            else:
                # CLI/dev mode: use path traversal fallback
                current_file = Path(__file__)
                workspace_dir = current_file.parent.parent.parent.parent

    dotenv_path = workspace_dir / ".env"

    # If we found a .env file, load it
    if dotenv_path.exists():
        loaded = load_dotenv(dotenv_path, override=True)
        if loaded:
            if verbose:
                logger.info(f".env file found and loaded from {dotenv_path}")
            return True
        else:
            if verbose:
                logger.warning(
                    f".env file found at {dotenv_path} but no variables were loaded."
                )
            return False

    # No .env file found
    if verbose:
        logger.info("No .env file found. Using system environment variables.")
    return False
