"""Configuration settings for the GUI backend."""

import os
import sys
from pathlib import Path
from typing import List, Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def is_production() -> bool:
    """Check if running in production mode.

    Tauri passes --production flag when launching the sidecar in production builds.
    This is more reliable than PyInstaller's sys.frozen attribute.

    Returns:
        True if running in production mode, False if in development.
    """
    return "--production" in sys.argv


def get_default_workspace_dir() -> Path:
    """Get the platform-specific workspace directory.

    Uses fixed, platform-appropriate paths that match Tauri's Application Support directory.
    Rust (Tauri) determines dev/prod mode and passes --production flag to Python in production.

    Development mode: Project root
    Production mode: Platform-specific Application Support directory
      - macOS: ~/Library/Application Support/Script to Speech/
      - Windows: %APPDATA%\\Script to Speech\\
      - Linux: ~/.local/share/script-to-speech/

    Returns:
        Path to the workspace directory.
    """
    # Check if Tauri passed the --production flag
    if not is_production():
        # Development mode: use project root (4 levels up from this file)
        # gui_backend/config.py -> gui_backend -> script_to_speech -> src -> project root
        return Path(__file__).parent.parent.parent.parent

    # Production mode: use platform-specific Application Support directory
    # This matches what Tauri uses for BaseDirectory::AppLocalData
    home = Path.home()

    if sys.platform == "darwin":  # macOS
        app_support = home / "Library" / "Application Support" / "Script to Speech"
    elif sys.platform == "win32":  # Windows
        appdata = os.getenv("APPDATA", str(home / "AppData" / "Roaming"))
        app_support = Path(appdata) / "Script to Speech"
    else:  # Linux and others
        xdg_data = os.getenv("XDG_DATA_HOME", str(home / ".local" / "share"))
        app_support = Path(xdg_data) / "script-to-speech"

    return app_support


class Settings(BaseSettings):
    """Application settings."""

    # Server settings
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    # Workspace directory - can be set via environment variable or CLI arg
    # Priority: STS_WORKSPACE_DIR env var > default location
    WORKSPACE_DIR: Optional[Path] = None

    # Legacy paths (kept for backward compatibility in development)
    STS_ROOT_DIR: Path = Path(__file__).parent.parent.parent.parent
    AUDIO_OUTPUT_DIR: Path = STS_ROOT_DIR / "standalone_speech"
    UPLOAD_DIR: Path = STS_ROOT_DIR / "uploads"

    # CORS settings
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:5173",  # Vite dev server
        "tauri://localhost",  # Tauri app
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",  # Ignore extra environment variables like API keys
    )

    @field_validator("WORKSPACE_DIR", mode="before")
    @classmethod
    def set_default_workspace(cls, v: Optional[str]) -> Path:
        """Set default workspace directory if not provided."""
        if v is None:
            return get_default_workspace_dir()
        return Path(v)

    def initialize_workspace(self) -> None:
        """Initialize workspace directories, creating them if they don't exist.

        Raises:
            PermissionError: If unable to create directories due to permissions
            OSError: If directory creation fails for other reasons
        """
        if self.WORKSPACE_DIR is None:
            raise ValueError("WORKSPACE_DIR is not set")

        try:
            # Create main workspace directory
            self.WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)

            # Create standard subdirectories
            (self.WORKSPACE_DIR / "input").mkdir(exist_ok=True)
            (self.WORKSPACE_DIR / "output").mkdir(exist_ok=True)
            (self.WORKSPACE_DIR / "source_screenplays").mkdir(exist_ok=True)

        except PermissionError as e:
            raise PermissionError(
                f"Permission denied when creating workspace at {self.WORKSPACE_DIR}. "
                f"Please check your permissions or set STS_WORKSPACE_DIR to a writable location."
            ) from e
        except OSError as e:
            raise OSError(
                f"Failed to create workspace directories at {self.WORKSPACE_DIR}: {e}"
            ) from e


# Create settings instance
settings = Settings()

# Initialize workspace directories (creates input/, output/, source_screenplays/)
try:
    settings.initialize_workspace()
except (PermissionError, OSError) as e:
    # Log the error but don't fail - let the services handle it gracefully
    import logging

    logger = logging.getLogger(__name__)
    logger.error(f"Failed to initialize workspace: {e}")

# Ensure legacy directories exist for backward compatibility (development mode)
settings.AUDIO_OUTPUT_DIR.mkdir(exist_ok=True)
settings.UPLOAD_DIR.mkdir(exist_ok=True)
