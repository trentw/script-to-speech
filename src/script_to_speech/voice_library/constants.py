"""Constants for voice library paths and configurations."""

import os
import sys
from pathlib import Path


def _get_user_workspace_dir() -> Path:
    """Get the workspace directory for user-writable config/data.

    Mirrors gui_backend/config.py:get_default_workspace_dir() to ensure
    USER_* paths resolve correctly in both dev and production builds.

    Development mode: Project root (Path.cwd(), set by Tauri .current_dir())
    Production mode: Platform-specific Application Support directory
    """
    if not getattr(sys, "frozen", False):
        return Path.cwd()

    home = Path.home()
    if sys.platform == "darwin":
        return home / "Library" / "Application Support" / "Script to Speech"
    elif sys.platform == "win32":
        localappdata = os.getenv("LOCALAPPDATA", str(home / "AppData" / "Local"))
        return Path(localappdata) / "Script to Speech"
    else:
        xdg_data = os.getenv("XDG_DATA_HOME", str(home / ".local" / "share"))
        return Path(xdg_data) / "script-to-speech"


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
        return (
            base_path / "script_to_speech" / "voice_library" / "voice_library_scripts"
        )
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
USER_VOICE_LIBRARY_PATH = (
    _get_user_workspace_dir() / "voice_library" / "voice_library_data"
)

# Voice library config paths
REPO_CONFIG_PATH = _get_voice_library_config_path()
USER_CONFIG_PATH = _get_user_workspace_dir() / "voice_library" / "voice_library_config"

# Voice library script paths
REPO_VOICE_LIBRARY_SCRIPTS_PATH = _get_voice_library_scripts_path()
USER_VOICE_LIBRARY_SCRIPTS_PATH = (
    _get_user_workspace_dir() / "voice_library" / "voice_library_scripts"
)
