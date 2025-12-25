"""Settings API router for managing application configuration."""

import os
from pathlib import Path

from dotenv import dotenv_values, load_dotenv, set_key
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..config import get_default_workspace_dir
from ..constants import ALLOWED_ENV_KEYS
from ..models import ApiResponse

router = APIRouter(prefix="/api/settings", tags=["settings"])

# Constants for API key masking display
MASKED_KEY_PREFIX_LENGTH = 3  # Show first 3 characters
MASKED_KEY_SUFFIX_LENGTH = 3  # Show last 3 characters
MASKED_KEY_STARS_COUNT = 9  # Fixed number of stars in middle
MASKED_KEY_MIN_LENGTH = MASKED_KEY_PREFIX_LENGTH + MASKED_KEY_SUFFIX_LENGTH + 1


class EnvKeyUpdate(BaseModel):
    """Request model for updating an environment variable."""

    key: str
    value: str


def get_env_file_path() -> Path:
    """Get .env file path using existing workspace detection logic.

    Returns same path whether in dev or prod mode, ensuring consistency
    with existing workspace directory management.

    Returns:
        Path to the .env file in the workspace directory.
    """
    workspace_dir = get_default_workspace_dir()
    return workspace_dir / ".env"


@router.get("/env")
async def get_env_keys() -> ApiResponse:
    """Read API keys from .env file (returns masked values).

    Returns masked API key values for display in the UI.
    Full keys are never sent to the frontend for security.

    Returns:
        ApiResponse with masked key values and .env file path.
    """
    env_path = get_env_file_path()

    try:
        if not env_path.exists():
            # Create empty .env if it doesn't exist
            env_path.parent.mkdir(parents=True, exist_ok=True)
            env_path.touch(mode=0o600)  # User read/write only

        env_vars = dotenv_values(env_path)

        # Return masked values for security
        # Format: first 3 chars + 9 stars + last 3 chars (max 15 chars total)
        masked = {}
        for key in ALLOWED_ENV_KEYS:
            value = env_vars.get(key, "")
            if value and len(value) >= MASKED_KEY_MIN_LENGTH:
                # Show first 3 + stars + last 3
                masked[key] = (
                    value[:MASKED_KEY_PREFIX_LENGTH]
                    + "*" * MASKED_KEY_STARS_COUNT
                    + value[-MASKED_KEY_SUFFIX_LENGTH:]
                )
            elif value:
                # Short keys: mask completely
                masked[key] = "*" * len(value)
            else:
                masked[key] = False  # Not configured

        return ApiResponse(
            ok=True,
            data={
                "keys": masked,
                "env_path": str(env_path),  # Show user where file is
            },
        )
    except PermissionError as e:
        return ApiResponse(
            ok=False,
            error="Permission denied accessing .env file",
            details={"path": str(env_path), "error": str(e)},
        )
    except Exception as e:
        return ApiResponse(
            ok=False,
            error=f"Failed to read .env file: {str(e)}",
            details={"path": str(env_path)},
        )


@router.post("/env")
async def update_env_key(update: EnvKeyUpdate) -> ApiResponse:
    """Update a single API key in .env file.

    Args:
        update: Environment variable key and value to update.

    Returns:
        ApiResponse indicating success or failure.

    Raises:
        HTTPException: If the key is not in the allowed whitelist.
    """
    if update.key not in ALLOWED_ENV_KEYS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid environment variable. Allowed: {', '.join(sorted(ALLOWED_ENV_KEYS))}",
        )

    env_path = get_env_file_path()

    try:
        if not env_path.exists():
            env_path.parent.mkdir(parents=True, exist_ok=True)
            env_path.touch(mode=0o600)

        # Use python-dotenv's set_key to safely update (preserves comments/formatting)
        set_key(env_path, update.key, update.value)

        # Reload environment variables so they're available immediately
        load_dotenv(env_path, override=True)

        return ApiResponse(ok=True, data={"key": update.key, "updated": True})
    except PermissionError as e:
        return ApiResponse(
            ok=False,
            error="Permission denied writing to .env file",
            details={"path": str(env_path), "error": str(e)},
        )
    except Exception as e:
        return ApiResponse(
            ok=False,
            error=f"Failed to update .env file: {str(e)}",
            details={"path": str(env_path)},
        )


@router.post("/env/validate")
async def validate_api_keys() -> ApiResponse:
    """Validate which API keys are currently configured in environment.

    Checks the current process environment for the presence of API keys.
    This is used to determine which providers are available.

    Returns:
        ApiResponse with boolean flags for each allowed key.
    """
    validation = {key: bool(os.environ.get(key)) for key in ALLOWED_ENV_KEYS}

    return ApiResponse(ok=True, data={"keys": validation})
