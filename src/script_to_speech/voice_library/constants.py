"""Constants for voice library paths and configurations."""

from pathlib import Path

# Voice library data paths
REPO_VOICE_LIBRARY_PATH = Path(__file__).parent / "voice_library_data"
USER_VOICE_LIBRARY_PATH = Path.cwd() / "voice_library" / "voice_library_data"

# Voice library config paths
REPO_CONFIG_PATH = Path(__file__).parent / "voice_library_config"
USER_CONFIG_PATH = Path.cwd() / "voice_library" / "voice_library_config"

# Voice library script paths
REPO_VOICE_LIBRARY_SCRIPTS_PATH = Path(__file__).parent / "voice_library_scripts"
USER_VOICE_LIBRARY_SCRIPTS_PATH = Path.cwd() / "voice_library" / "voice_library_scripts"
