"""Schema loading and merging utilities for voice library."""

from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from ..utils.dict_utils import deep_merge
from ..utils.logging import get_screenplay_logger
from .constants import REPO_VOICE_LIBRARY_PATH, USER_VOICE_LIBRARY_PATH

logger = get_screenplay_logger("voice_library.schema_utils")


def load_schema_file(file_path: Path, description: str) -> Optional[Dict[str, Any]]:
    """
    Load and parse a YAML schema file with error handling.

    Args:
        file_path: Path to the YAML file
        description: Human-readable description for error messages

    Returns:
        Parsed YAML data or None if error occurred
    """
    if not file_path.exists():
        logger.debug(f"{description} not found at {file_path}")
        return None

    try:
        with open(file_path, "r") as f:
            data = yaml.safe_load(f)
            if data is None:
                logger.warning(f"{description} is empty")
                return None
            if not isinstance(data, dict):
                logger.error(f"{description} must be a dictionary")
                return None
            logger.debug(f"Loaded {description} from {file_path}")
            return data
    except yaml.YAMLError as e:
        logger.error(f"YAML error in {description}: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Error loading {description}: {str(e)}")
        return None


def merge_schemas(schemas: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Deep merge multiple schemas with later schemas taking precedence.

    Args:
        schemas: List of schema dictionaries to merge, in order of increasing precedence

    Returns:
        Merged schema dictionary
    """
    if not schemas:
        return {}

    merged_schema: Dict[str, Any] = {}
    for schema in schemas:
        if schema:
            merged_schema = deep_merge(merged_schema, schema)

    return merged_schema


def load_merged_schemas_for_providers(providers: List[str]) -> Dict[str, Any]:
    """
    Load and merge global schemas plus all provider schemas for the given providers.

    Merges schemas in order of precedence:
    1. Project global schema (lowest precedence)
    2. User global schema
    3. Project provider schemas (in order of providers list)
    4. User provider schemas (in order of providers list, highest precedence)

    Args:
        providers: List of provider names to include schemas for

    Returns:
        Merged schema dictionary including global + all provider schemas

    Raises:
        ValueError: If no global schema files are found
    """
    schemas = []
    schema_sources = []

    # 1. Project global schema
    project_global_path = REPO_VOICE_LIBRARY_PATH / "voice_library_schema.yaml"
    project_global = load_schema_file(project_global_path, "Project global schema")
    if project_global:
        schemas.append(project_global)
        schema_sources.append("project global")

    # 2. User global schema
    user_global_path = USER_VOICE_LIBRARY_PATH / "voice_library_schema.yaml"
    user_global = load_schema_file(user_global_path, "User global schema")
    if user_global:
        schemas.append(user_global)
        schema_sources.append("user global")

    # Must have at least project global schema
    if not schemas:
        raise ValueError(
            f"No global schema files found. At minimum, project global schema is required at: {project_global_path}"
        )

    # 3. Project provider schemas (in order of providers list)
    for provider in providers:
        project_provider_path = (
            REPO_VOICE_LIBRARY_PATH / provider / "provider_schema.yaml"
        )
        project_provider = load_schema_file(
            project_provider_path, f"Project {provider} provider schema"
        )
        if project_provider:
            schemas.append(project_provider)
            schema_sources.append(f"project {provider} provider")

    # 4. User provider schemas (in order of providers list)
    for provider in providers:
        user_provider_path = USER_VOICE_LIBRARY_PATH / provider / "provider_schema.yaml"
        user_provider = load_schema_file(
            user_provider_path, f"User {provider} provider schema"
        )
        if user_provider:
            schemas.append(user_provider)
            schema_sources.append(f"user {provider} provider")

    logger.info(
        f"Merging schemas for providers {providers}: {', '.join(schema_sources)}"
    )
    return merge_schemas(schemas)
