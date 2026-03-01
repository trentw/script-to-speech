"""Settings API router for managing application configuration."""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from dotenv import dotenv_values, load_dotenv, set_key
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from script_to_speech.voice_library.constants import USER_CONFIG_PATH

from ..config import get_default_workspace_dir
from ..constants import ALLOWED_ENV_KEYS
from ..models import ApiResponse

CASTING_INSTRUCTIONS_FILENAME = "casting_instructions.yaml"

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


# ── Casting Instructions ──────────────────────────────────────────────────


class CastingInstructionItem(BaseModel):
    """A single casting instruction with enabled state."""

    text: str
    enabled: bool = True


class CastingInstructionsUpdate(BaseModel):
    """Request model for updating casting instructions."""

    overall: List[CastingInstructionItem] = []
    provider_instructions: Dict[str, List[CastingInstructionItem]] = {}


def _get_casting_instructions_path() -> Path:
    return USER_CONFIG_PATH / CASTING_INSTRUCTIONS_FILENAME


def _read_casting_instructions() -> Dict[str, Any]:
    """Read casting instructions YAML file and return structured data."""
    path = _get_casting_instructions_path()
    if not path.exists():
        return {"overall": [], "provider_instructions": {}}

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not data or not isinstance(data, dict):
        return {"overall": [], "provider_instructions": {}}

    raw = data.get("additional_voice_casting_instructions", {})
    if not isinstance(raw, dict):
        return {"overall": [], "provider_instructions": {}}

    result: Dict[str, Any] = {"overall": [], "provider_instructions": {}}

    for key, items in raw.items():
        if not isinstance(items, list):
            continue
        parsed: List[Dict[str, Any]] = []
        for item in items:
            if isinstance(item, dict) and "text" in item:
                parsed.append(
                    {"text": item["text"], "enabled": item.get("enabled", True)}
                )
            elif isinstance(item, str):
                parsed.append({"text": item, "enabled": True})

        if key == "overall_voice_casting_prompt":
            result["overall"] = parsed
        else:
            result["provider_instructions"][key] = parsed

    return result


def _write_casting_instructions(data: CastingInstructionsUpdate) -> None:
    """Write structured casting instructions to YAML file."""
    yaml_data: Dict[str, Any] = {}

    if data.overall:
        yaml_data["overall_voice_casting_prompt"] = [
            {"text": item.text, "enabled": item.enabled} for item in data.overall
        ]

    for provider, items in data.provider_instructions.items():
        if items:
            yaml_data[provider] = [
                {"text": item.text, "enabled": item.enabled} for item in items
            ]

    path = _get_casting_instructions_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    output = {"additional_voice_casting_instructions": yaml_data} if yaml_data else {}

    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(
            output, f, default_flow_style=False, allow_unicode=True, sort_keys=False
        )


@router.get("/casting-instructions")
async def get_casting_instructions() -> ApiResponse:
    """Read casting instructions from workspace YAML file."""
    try:
        data = _read_casting_instructions()
        return ApiResponse(ok=True, data=data)
    except Exception as e:
        return ApiResponse(
            ok=False,
            error=f"Failed to read casting instructions: {str(e)}",
        )


@router.put("/casting-instructions")
async def update_casting_instructions(update: CastingInstructionsUpdate) -> ApiResponse:
    """Write full casting instruction set to workspace YAML file."""
    try:
        _write_casting_instructions(update)
        data = _read_casting_instructions()
        return ApiResponse(ok=True, data=data)
    except Exception as e:
        return ApiResponse(
            ok=False,
            error=f"Failed to update casting instructions: {str(e)}",
        )
