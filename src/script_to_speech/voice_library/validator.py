"""Voice library validation functionality."""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import yaml

from ..tts_providers.tts_provider_manager import TTSProviderManager
from ..utils.logging import get_screenplay_logger

logger = get_screenplay_logger("voice_library.validator")


class VoiceLibraryValidator:
    """Validates voice library YAML files against schemas."""

    def __init__(self, library_root: Optional[Path] = None):
        """
        Initialize the validator.

        Args:
            library_root: Root directory of voice library data.
                         Defaults to src/script_to_speech/voice_library/voice_library_data
        """
        if library_root is None:
            # Default to voice_library_data subdirectory
            module_dir = Path(__file__).parent
            library_root = module_dir / "voice_library_data"

        self.library_root = Path(library_root)
        self.global_schema: Dict[str, Any] = {}
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
        Validate all voice libraries.

        Returns:
            Tuple of (is_valid, list_of_error_messages)
        """
        self.validation_errors = []

        # Load global schema
        global_schema_path = self.library_root / "voice_library_schema.yaml"
        loaded_schema = self._load_yaml_file(global_schema_path, "Global schema")
        if loaded_schema is None:
            return False, self.validation_errors
        self.global_schema = loaded_schema

        # Validate each provider directory
        for provider_dir in self.library_root.iterdir():
            if provider_dir.is_dir() and not provider_dir.name.startswith("."):
                self._validate_provider_directory(provider_dir)

        return len(self.validation_errors) == 0, self.validation_errors

    def _validate_provider_directory(self, provider_dir: Path) -> None:
        """Validate all voice files in a provider directory."""
        provider_name = provider_dir.name
        logger.info(f"Validating provider: {provider_name}")

        # Load provider-specific schema if it exists
        provider_schema_path = provider_dir / "provider_schema.yaml"
        provider_schema: Dict[str, Any] = {}
        if provider_schema_path.exists():
            loaded_provider_schema = self._load_yaml_file(
                provider_schema_path, f"{provider_name} provider schema"
            )
            if loaded_provider_schema is None:
                return  # Error already logged
            provider_schema = loaded_provider_schema

        # Combine schemas
        combined_schema = self._merge_schemas(self.global_schema, provider_schema)

        # Validate each voice file
        voice_files_found = False
        for voice_file in provider_dir.glob("*.yaml"):
            if voice_file.name != "provider_schema.yaml":
                voice_files_found = True
                self._validate_voice_file(voice_file, provider_name, combined_schema)

        if not voice_files_found:
            self.validation_errors.append(
                f"No voice files found in {provider_name} directory"
            )

    def _merge_schemas(
        self, global_schema: Dict[str, Any], provider_schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Merge global and provider-specific schemas."""
        merged = global_schema.copy()

        # Merge voice_properties if present in provider schema
        if "voice_properties" in provider_schema:
            if "voice_properties" not in merged:
                merged["voice_properties"] = {}
            merged["voice_properties"].update(provider_schema["voice_properties"])

        # Add any provider-specific sections
        for key, value in provider_schema.items():
            if key not in merged:
                merged[key] = value

        return merged

    def _validate_voice_file(
        self, voice_file: Path, provider_name: str, schema: Dict[str, Any]
    ) -> None:
        """Validate a single voice library file."""
        logger.info(f"  Validating file: {voice_file.name}")

        voice_data = self._load_yaml_file(voice_file, f"Voice file {voice_file.name}")
        if voice_data is None:
            return  # Error already logged

        if not isinstance(voice_data, dict):
            self.validation_errors.append(
                f"{provider_name}/{voice_file.name}: Root must be a dictionary"
            )
            return

        # Validate voices section
        if "voices" not in voice_data:
            self.validation_errors.append(
                f"{provider_name}/{voice_file.name}: Missing 'voices' section"
            )
            return

        voices = voice_data["voices"]
        if not isinstance(voices, dict):
            self.validation_errors.append(
                f"{provider_name}/{voice_file.name}: 'voices' must be a dictionary"
            )
            return

        # Validate each voice
        for voice_id, voice_config in voices.items():
            self._validate_single_voice(
                voice_file.name, voice_id, voice_config, provider_name, schema
            )

    def _validate_single_voice(
        self,
        file_name: str,
        voice_id: str,
        voice_config: Dict[str, Any],
        provider_name: str,
        schema: Dict[str, Any],
    ) -> None:
        """Validate a single voice configuration."""
        voice_ref = f"{provider_name}/{file_name}[{voice_id}]"  # e.g., "openai/voices.yaml[onyx]"

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
