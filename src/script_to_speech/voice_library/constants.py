"""Constants for voice library paths and configurations."""

import sys
from pathlib import Path


def _get_voice_library_path() -> Path:
    """Get the repo voice library path, handling PyInstaller builds."""
    if getattr(sys, "frozen", False):
        base_path = Path(getattr(sys, "_MEIPASS", "."))
        return base_path / "script_to_speech" / "voice_library" / "voice_library_data"
    else:
        return Path(__file__).parent / "voice_library_data"


def _get_voice_library_scripts_path() -> Path:
    """Get the repo voice library scripts path, handling PyInstaller builds."""
    if getattr(sys, "frozen", False):
        # Note: Scripts may not be bundled, return a path that won't exist
        base_path = Path(getattr(sys, "_MEIPASS", "."))
        return base_path / "script_to_speech" / "voice_library" / "voice_library_scripts"
    else:
        return Path(__file__).parent / "voice_library_scripts"


def _get_voice_library_config_path() -> Path:
    """Get the repo voice library config path, handling PyInstaller builds."""
    if getattr(sys, "frozen", False):
        base_path = Path(getattr(sys, "_MEIPASS", "."))
        return base_path / "script_to_speech" / "voice_library" / "voice_library_config"
    else:
        return Path(__file__).parent / "voice_library_config"


# Voice library data paths
REPO_VOICE_LIBRARY_PATH = _get_voice_library_path()
USER_VOICE_LIBRARY_PATH = Path.cwd() / "voice_library" / "voice_library_data"

# Voice library config paths
REPO_CONFIG_PATH = _get_voice_library_config_path()
USER_CONFIG_PATH = Path.cwd() / "voice_library" / "voice_library_config"

# Voice library script paths
REPO_VOICE_LIBRARY_SCRIPTS_PATH = _get_voice_library_scripts_path()
USER_VOICE_LIBRARY_SCRIPTS_PATH = Path.cwd() / "voice_library" / "voice_library_scripts"
