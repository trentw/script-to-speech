"""
Utilities for voice library scripts.
"""

from pathlib import Path
from typing import Optional

from .constants import REPO_VOICE_LIBRARY_SCRIPTS_PATH, USER_VOICE_LIBRARY_SCRIPTS_PATH


def find_provider_specific_file(
    script_name: str, provider: str, target_filename: str
) -> Optional[Path]:
    """
    Finds a provider-specific file for a voice library script, giving user-defined files precedence.

    Args:
        script_name: The name of the script (e.g., 'fetch_available_voices').
        provider: The name of the provider (e.g., 'elevenlabs').
        target_filename: The specific file to search for (e.g., 'fetch_provider_voices.py').

    Returns:
        The Path to the file if found, otherwise None.
    """
    # User path takes precedence
    user_path = (
        USER_VOICE_LIBRARY_SCRIPTS_PATH / script_name / provider / target_filename
    )
    if user_path.is_file():
        return user_path

    # System path is the fallback
    repo_path = (
        REPO_VOICE_LIBRARY_SCRIPTS_PATH / script_name / provider / target_filename
    )
    if repo_path.is_file():
        return repo_path

    return None
