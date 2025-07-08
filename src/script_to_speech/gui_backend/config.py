"""Configuration settings for the GUI backend."""

import os
from pathlib import Path
from typing import List

try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # Server settings
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    
    # File paths
    STS_ROOT_DIR: Path = Path(__file__).parent.parent.parent.parent
    AUDIO_OUTPUT_DIR: Path = STS_ROOT_DIR / "gui_audio_output"
    
    # CORS settings
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:5173",  # Vite dev server
        "tauri://localhost",      # Tauri app
    ]
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignore extra environment variables like API keys


# Create settings instance
settings = Settings()

# Ensure audio output directory exists
settings.AUDIO_OUTPUT_DIR.mkdir(exist_ok=True)