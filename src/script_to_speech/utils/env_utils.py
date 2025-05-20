"""
Utility module for loading environment variables from .env files.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

from script_to_speech.utils.logging import get_screenplay_logger

# Define logger for this module
logger = get_screenplay_logger("utils.env_utils")


def load_environment_variables(verbose: bool = True) -> bool:
    """
    Load environment variables from a .env file in the project root.

    This function looks for a .env file in the project root directory
    (where pyproject.toml is located) and loads any environment variables
    defined in it. It's primarily used to load API keys for TTS providers.

    Args:
        verbose: Whether to log information about the .env file loading

    Returns:
        bool: True if a .env file was found and loaded, False otherwise
    """
    # The .env file should be in the project root, which is 3 directories up from this file
    # This file is in src/script_to_speech/utils/env_utils.py
    current_file = Path(__file__)
    project_root = current_file.parent.parent.parent.parent
    dotenv_path = project_root / ".env"

    # If we found a .env file, load it
    if dotenv_path.exists():
        loaded = load_dotenv(dotenv_path)
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
