"""Voice library validation functionality."""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import yaml

from ..tts_providers.tts_provider_manager import TTSProviderManager
from ..utils.logging import get_screenplay_logger
from .constants import REPO_VOICE_LIBRARY_PATH, USER_VOICE_LIBRARY_PATH
from .schema_utils import load_merged_schemas_for_providers

logger = get_screenplay_logger("voice_library.validator")


class VoiceLibraryValidator:
    """Validates voice library YAML files against schemas."""

    def __init__(self, project_only: bool = False):
        """
        Initialize the validator.

        Args:
            project_only: If True, validate only the project voice library.
                         If False, validate both project and user voice libraries.
        """
        self.project_only = project_only
        self.validation_errors: List[str] = []

    def _load_yaml_file(
        self, file_path: Path, description: str
    ) -> Optional[Dict[str, Any]]:
        """
        Load and parse a YAML file with error handling.

        Args:
            file_path: Path to the YAML file
            description: Human-readable description for error messages

        Returns:
            Parsed YAML data or None if error occurred
        """
        if not file_path.exists():
            self.validation_errors.append(f"{description} not found at {file_path}")
            return None

        try:
            with open(file_path, "r") as f:
                data = yaml.safe_load(f)
                if data is None:
                    self.validation_errors.append(f"{description} is empty")
                    return None
                if not isinstance(data, dict):
                    self.validation_errors.append(f"{description} must be a dictionary")
                    return None
                return data
        except yaml.YAMLError as e:
            self.validation_errors.append(f"YAML error in {description}: {str(e)}")
            return None
        except Exception as e:
            self.validation_errors.append(f"Error loading {description}: {str(e)}")
            return None

    def validate_all(self) -> Tuple[bool, List[str]]:
        """
        Validate voice libraries.

        Validates project voice library and optionally user voice library
        based on the project_only setting.

        Returns:
            Tuple of (is_valid, list_of_error_messages)
        """
        self.validation_errors = []

        # Validate project voice library
        self._validate_library_directory(REPO_VOICE_LIBRARY_PATH, "project")

        # Validate user voice library if not project-only mode
        if not self.project_only:
            self._validate_library_directory(USER_VOICE_LIBRARY_PATH, "user")

        return len(self.validation_errors) == 0, self.validation_errors

    def _validate_library_directory(self, library_root: Path, source: str) -> None:
        """
        Validate all provider directories in a voice library directory.

        Args:
            library_root: Root directory containing provider subdirectories
            source: Source description ("project" or "user") for error messages
        """
        if not library_root.exists() or not library_root.is_dir():
            # User directory might not exist, which is fine
            if source == "user":
                return
            # Project directory should exist
            self.validation_errors.append(
                f"Voice library directory not found: {library_root}"
            )
            return

        # Validate each provider directory
        for provider_dir in library_root.iterdir():
            if provider_dir.is_dir() and not provider_dir.name.startswith("."):
                self._validate_provider_directory(provider_dir, source)

    def _validate_provider_directory(self, provider_dir: Path, source: str) -> None:
        """
        Validate all voice files in a provider directory.

        Args:
            provider_dir: Directory containing voice files for a provider
            source: Source description ("project" or "user") for error messages
        """
        provider_name = provider_dir.name
        logger.info(f"Validating {source} provider: {provider_name}")

        # Load merged schema for this provider
        try:
            combined_schema = load_merged_schemas_for_providers([provider_name])
        except ValueError as e:
            self.validation_errors.append(f"Schema error for {provider_name}: {str(e)}")
            return

        # Validate each voice library file
        voice_library_files_found = False
        for voice_library_file in provider_dir.glob("*.yaml"):
            if voice_library_file.name != "provider_schema.yaml":
                voice_library_files_found = True
                self._validate_voice_library_file(
                    voice_library_file, provider_name, combined_schema, source
                )

        if not voice_library_files_found:
            self.validation_errors.append(
                f"No voice files found in {source} {provider_name} directory"
            )

    def _validate_voice_library_file(
        self,
        voice_library_file: Path,
        provider_name: str,
        schema: Dict[str, Any],
        source: str,
    ) -> None:
        """
        Validate a single voice library file.

        Args:
            voice_library_file: Path to the voice library file
            provider_name: Name of the provider
            schema: Combined schema for validation
            source: Source description ("project" or "user") for error messages
        """
        logger.info(f"  Validating {source} file: {voice_library_file.name}")

        voice_data = self._load_yaml_file(
            voice_library_file, f"Voice file {voice_library_file.name}"
        )
        if voice_data is None:
            return  # Error already logged

        if not isinstance(voice_data, dict):
            self.validation_errors.append(
                f"{source} {provider_name}/{voice_library_file.name}: Root must be a dictionary"
            )
            return

        # Validate voices section
        if "voices" not in voice_data:
            self.validation_errors.append(
                f"{source} {provider_name}/{voice_library_file.name}: Missing 'voices' section"
            )
            return

        voices = voice_data["voices"]
        if not isinstance(voices, dict):
            self.validation_errors.append(
                f"{source} {provider_name}/{voice_library_file.name}: 'voices' must be a dictionary"
            )
            return

        # Validate each voice
        for voice_id, voice_config in voices.items():
            self._validate_single_voice(
                voice_library_file.name,
                voice_id,
                voice_config,
                provider_name,
                schema,
                source,
            )

    def _validate_single_voice(
        self,
        file_name: str,
        voice_id: str,
        voice_config: Dict[str, Any],
        provider_name: str,
        schema: Dict[str, Any],
        source: str,
    ) -> None:
        """
        Validate a single voice configuration.

        Args:
            file_name: Name of the voice file
            voice_id: ID of the voice
            voice_config: Configuration for the voice
            provider_name: Name of the provider
            schema: Combined schema for validation
            source: Source description ("project" or "user") for error messages
        """
        voice_ref = f"{source} {provider_name}/{file_name}[{voice_id}]"  # e.g., "project openai/voices.yaml[onyx]"

        if not isinstance(voice_config, dict):
            self.validation_errors.append(
                f"{voice_ref}: Voice configuration must be a dictionary"
            )
            return

        # Validate required top-level fields
        required_fields = ["config", "voice_properties", "description"]
        for field in required_fields:
            if field not in voice_config:
                self.validation_errors.append(
                    f"{voice_ref}: Missing required field '{field}'"
                )

        # Validate config section
        if "config" in voice_config:
            self._validate_voice_config(
                voice_ref, voice_config["config"], provider_name
            )

        # Validate voice_properties against schema
        if "voice_properties" in voice_config and "voice_properties" in schema:
            self._validate_voice_properties(
                voice_ref, voice_config["voice_properties"], schema["voice_properties"]
            )

        # Validate description is a dict
        if "description" in voice_config:
            if not isinstance(voice_config["description"], dict):
                self.validation_errors.append(
                    f"{voice_ref}: 'description' must be a dictionary"
                )

    def _validate_voice_config(
        self, voice_ref: str, config: Dict[str, Any], provider_name: str
    ) -> None:
        """Validate the config section using TTS provider validation."""
        if not isinstance(config, dict):
            self.validation_errors.append(f"{voice_ref}: 'config' must be a dictionary")
            return

        # Create a temporary config with provider for validation
        # (TTS provider validation expects it, but we don't store it)
        temp_config = config.copy()
        temp_config["provider"] = provider_name

        # Use TTS provider validation
        try:
            provider_class = TTSProviderManager._get_provider_class(provider_name)
            provider_class.validate_speaker_config(temp_config)
        except Exception as e:
            self.validation_errors.append(f"{voice_ref}: Invalid TTS config - {str(e)}")

    def _validate_voice_properties(
        self,
        voice_ref: str,
        properties: Dict[str, Any],
        schema_properties: Dict[str, Any],
    ) -> None:
        """Validate voice properties against schema."""
        if not isinstance(properties, dict):
            self.validation_errors.append(
                f"{voice_ref}: 'voice_properties' must be a dictionary"
            )
            return

        # Check each property against schema
        for prop_name, prop_value in properties.items():
            if prop_name not in schema_properties:
                self.validation_errors.append(
                    f"{voice_ref}: Unknown voice property '{prop_name}'"
                )
                continue

            prop_schema = schema_properties[prop_name]
            self._validate_property_value(voice_ref, prop_name, prop_value, prop_schema)

        # Check for mirror property conflicts
        self._check_mirror_properties(voice_ref, properties, schema_properties)

    def _validate_property_value(
        self,
        voice_ref: str,
        prop_name: str,
        prop_value: Any,
        prop_schema: Dict[str, Any],
    ) -> None:
        """Validate a single property value against its schema."""
        prop_type = prop_schema.get("type")

        if prop_type == "range":
            if not isinstance(prop_value, (int, float)):
                self.validation_errors.append(
                    f"{voice_ref}: Property '{prop_name}' must be a number"
                )
                return

            min_val = prop_schema.get("min", 0.0)
            max_val = prop_schema.get("max", 1.0)
            if not min_val <= prop_value <= max_val:
                self.validation_errors.append(
                    f"{voice_ref}: Property '{prop_name}' value {prop_value} "
                    f"outside range [{min_val}, {max_val}]"
                )

        elif prop_type == "enum":
            allowed_values = prop_schema.get("values", [])
            if prop_value not in allowed_values:
                self.validation_errors.append(
                    f"{voice_ref}: Property '{prop_name}' value '{prop_value}' "
                    f"not in allowed values: {allowed_values}"
                )

        elif prop_type == "boolean":
            if not isinstance(prop_value, bool):
                self.validation_errors.append(
                    f"{voice_ref}: Property '{prop_name}' must be a boolean"
                )

        elif prop_type == "text":
            if not isinstance(prop_value, str):
                self.validation_errors.append(
                    f"{voice_ref}: Property '{prop_name}' must be a string"
                )

    def _check_mirror_properties(
        self,
        voice_ref: str,
        properties: Dict[str, Any],
        schema_properties: Dict[str, Any],
    ) -> None:
        """Check that mirror properties aren't both specified."""
        # Build mirror property pairs
        mirror_pairs: Set[Tuple[str, str]] = set()
        for prop_name, prop_schema in schema_properties.items():
            if "mirror_of" in prop_schema:
                mirror_name = prop_schema["mirror_of"]
                # Add both directions to avoid duplicates
                pair = tuple(sorted([prop_name, mirror_name]))
                mirror_pairs.add(pair)

        # Check each pair
        for prop1, prop2 in mirror_pairs:
            if prop1 in properties and prop2 in properties:
                self.validation_errors.append(
                    f"{voice_ref}: Cannot specify both mirror properties "
                    f"'{prop1}' and '{prop2}'"
                )
