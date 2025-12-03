"""Configuration settings for the GUI backend."""

import os
import sys
from pathlib import Path
from typing import List, Optional

from pydantic import Field, field_validator
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

    Uses sys.frozen to detect production builds (PyInstaller executables).
    This is more reliable than --production flag for multiprocessing workers,
    as sys.frozen persists across all processes but sys.argv doesn't on macOS.

    Development mode: Project root
    Production mode: Platform-specific Application Support directory
      - macOS: ~/Library/Application Support/Script to Speech/
      - Windows: %APPDATA%\\Script to Speech\\
      - Linux: ~/.local/share/script-to-speech/

    Returns:
        Path to the workspace directory.
    """
    # Check if running as PyInstaller frozen executable
    # This works in both main process and multiprocessing workers
    if not getattr(sys, "frozen", False):
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
    # Port configuration: dev mode uses 8000, production uses 58735
    DEV_PORT: int = 8000
    PROD_PORT: int = 58735
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    @property
    def PORT(self) -> int:
        """Get the appropriate port based on mode (dev=8000, prod=58735)."""
        return self.PROD_PORT if is_production() else self.DEV_PORT

    # Workspace directory - can be set via environment variable or CLI arg
    # Priority: STS_WORKSPACE_DIR env var > default location
    # Note: Initialized as None, but field validator ensures it's always converted to Path.
    # This is a standard Pydantic pattern where validators enforce non-None at runtime,
    # but mypy cannot track the transformation, requiring the type: ignore annotation.
    WORKSPACE_DIR: Path = None  # type: ignore[assignment]

    @property
    def AUDIO_OUTPUT_DIR(self) -> Path:
        """Get the standalone speech output directory (workspace-relative)."""
        return self.WORKSPACE_DIR / "standalone_speech"

    @property
    def UPLOAD_DIR(self) -> Path:
        """Get the uploads directory (workspace-relative)."""
        return self.WORKSPACE_DIR / "uploads"

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
    def validate_workspace_dir(cls, v: Optional[str] | Path) -> Path:
        """Ensure workspace directory is always set to a valid Path.

        Handles:
        - None or empty string: Uses default workspace directory
        - String path: Converts to Path (e.g., from STS_WORKSPACE_DIR env var)
        - Path object: Returns as-is
        """
        if v is None or v == "":
            return get_default_workspace_dir()
        if isinstance(v, str):
            return Path(v)
        return v

    def initialize_workspace(self) -> None:
        """Initialize workspace directories, creating them if they don't exist.

        Raises:
            PermissionError: If unable to create directories due to permissions
            OSError: If directory creation fails for other reasons
        """
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


# Initialization guard to prevent duplicate setup in multiprocessing child processes
_initialized = False


def _initialize_settings_once() -> None:
    """Initialize settings and workspace only once, even across re-imports.

    This guard is MANDATORY for PyInstaller + multiprocessing to prevent:
    - Duplicate logging messages
    - Multiple workspace initialization attempts
    - Resource conflicts in child processes
    """
    global _initialized
    if _initialized:
        return

    _initialized = True

    # Log configuration information
    import logging

    logger = logging.getLogger(__name__)
    mode = "production" if is_production() else "development"
    logger.info(f"Backend configured for {mode} mode on port {settings.PORT}")

    # Initialize workspace directories (creates input/, output/, source_screenplays/)
    try:
        settings.initialize_workspace()
    except (PermissionError, OSError) as e:
        # Log the error but don't fail - let the services handle it gracefully
        logger.error(f"Failed to initialize workspace: {e}")

    # Ensure additional workspace directories exist
    settings.AUDIO_OUTPUT_DIR.mkdir(exist_ok=True)
    settings.UPLOAD_DIR.mkdir(exist_ok=True)


# Create settings instance
settings = Settings()

# Initialize settings once (guarded against multiprocessing re-imports)
_initialize_settings_once()
