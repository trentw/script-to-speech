"""Provider introspection service."""

import json
import logging
from typing import Any, Dict, List, Type, Union

from script_to_speech.tts_providers.base.stateful_tts_provider import (
    StatefulTTSProviderBase,
)
from script_to_speech.tts_providers.base.stateless_tts_provider import (
    StatelessTTSProviderBase,
)
from script_to_speech.tts_providers.tts_provider_manager import TTSProviderManager
from script_to_speech.utils.generate_standalone_speech import get_provider_class

from ..models import FieldType, ProviderField, ProviderInfo, ValidationResult

logger = logging.getLogger(__name__)


class ProviderService:
    """Service for TTS provider introspection and management."""

    def __init__(self) -> None:
        """Initialize the provider service."""
        self._providers_cache: Dict[str, ProviderInfo] = {}
        self._load_providers()

    def _load_providers(self) -> None:
        """Load and cache provider information."""
        try:
            available_providers = TTSProviderManager.get_available_providers()
            # Filter out dummy providers for GUI
            real_providers = [
                p for p in available_providers if not p.startswith("dummy_")
            ]

            for provider_name in real_providers:
                try:
                    provider_class = get_provider_class(provider_name)
                    provider_info = self._extract_provider_info(
                        provider_name, provider_class
                    )
                    self._providers_cache[provider_name] = provider_info
                    logger.info(f"Loaded provider: {provider_name}")
                except Exception as e:
                    logger.warning(f"Failed to load provider {provider_name}: {e}")
        except Exception as e:
            logger.error(f"Failed to load providers: {e}")

    def _extract_provider_info(
        self,
        provider_name: str,
        provider_class: Type[Union[StatelessTTSProviderBase, StatefulTTSProviderBase]],
    ) -> ProviderInfo:
        """Extract provider information from provider class."""

        # Get field information
        required_fields = provider_class.get_required_fields()
        optional_fields = provider_class.get_optional_fields()

        # Convert to ProviderField objects
        required_field_objects = [
            self._create_provider_field(field, True, provider_name, provider_class)
            for field in required_fields
        ]

        optional_field_objects = [
            self._create_provider_field(field, False, provider_name, provider_class)
            for field in optional_fields
        ]

        # Get max threads
        max_threads = provider_class.get_max_download_threads()

        return ProviderInfo(
            identifier=provider_name,
            name=provider_name.title(),
            description=f"{provider_name.title()} TTS Provider",
            required_fields=required_field_objects,
            optional_fields=optional_field_objects,
            max_threads=max_threads,
        )

    def _create_provider_field(
        self,
        field_name: str,
        required: bool,
        provider_name: str,
        provider_class: Type[Union[StatelessTTSProviderBase, StatefulTTSProviderBase]],
    ) -> ProviderField:
        """Create a ProviderField from field name and provider class."""

        # Try to infer field type and constraints from provider
        field_type = FieldType.STRING  # Default
        options = None
        min_value = None
        max_value = None
        description = None
        default = None

        # Provider-specific field handling
        if provider_name == "openai":
            if field_name == "voice":
                options = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
                description = "OpenAI voice identifier"
        elif provider_name == "elevenlabs":
            if field_name == "voice_id":
                description = "ElevenLabs voice ID"
        elif provider_name == "cartesia":
            if field_name == "voice_id":
                description = "Cartesia voice identifier"
            elif field_name == "language":
                description = "Language code (e.g., 'en')"
            elif field_name == "speed":
                field_type = FieldType.FLOAT
                min_value = 0.5
                max_value = 2.0
                description = "Speech speed multiplier"
        elif provider_name == "minimax":
            if field_name == "voice_id":
                description = "Minimax voice identifier"
            elif field_name == "voice_mix":
                field_type = FieldType.LIST
                description = "List of voice mix configurations"
            elif field_name == "speed":
                field_type = FieldType.FLOAT
                min_value = 0.5
                max_value = 2.0
                description = "Speech speed"
            elif field_name == "volume":
                field_type = FieldType.INTEGER
                min_value = 0
                max_value = 10
                description = "Audio volume level"
            elif field_name == "pitch":
                field_type = FieldType.FLOAT
                min_value = -12.0
                max_value = 12.0
                description = "Pitch adjustment in semitones"
            elif field_name == "emotion":
                options = ["happy", "sad", "angry", "surprised", "fearful", "disgusted"]
                description = "Emotional tone"
            elif field_name == "english_normalization":
                field_type = FieldType.BOOLEAN
                description = "Apply English text normalization"
            elif field_name == "language_boost":
                field_type = FieldType.BOOLEAN
                description = "Boost language-specific features"
        elif provider_name == "zonos":
            if field_name == "default_voice_name":
                description = "Zonos voice name"
            elif field_name == "speaking_rate":
                field_type = FieldType.FLOAT
                min_value = 0.5
                max_value = 2.0
                description = "Speaking rate multiplier"
            elif field_name == "language_iso_code":
                description = "ISO language code"

        return ProviderField(
            name=field_name,
            type=field_type,
            required=required,
            description=description,
            default=default,
            options=options,
            min_value=min_value,
            max_value=max_value,
        )

    def get_available_providers(self) -> List[str]:
        """Get list of available provider identifiers."""
        return list(self._providers_cache.keys())

    def get_provider_info(self, provider_name: str) -> ProviderInfo:
        """Get detailed information about a provider."""
        if provider_name not in self._providers_cache:
            raise ValueError(f"Provider {provider_name} not found")
        return self._providers_cache[provider_name]

    def get_all_providers(self) -> List[ProviderInfo]:
        """Get information about all available providers."""
        return list(self._providers_cache.values())

    def validate_config(
        self, provider_name: str, config: Dict[str, Any]
    ) -> ValidationResult:
        """Validate a provider configuration."""
        errors = []
        warnings = []

        try:
            if provider_name not in self._providers_cache:
                errors.append(f"Provider {provider_name} not found")
                return ValidationResult(valid=False, errors=errors)

            provider_class = get_provider_class(provider_name)

            # Create a copy of config with provider field
            full_config = config.copy()
            full_config["provider"] = provider_name

            # Try to validate using the provider's validation method
            try:
                provider_class.validate_speaker_config(full_config)
            except Exception as e:
                errors.append(str(e))

            # Check required fields
            provider_info = self._providers_cache[provider_name]
            required_field_names = [f.name for f in provider_info.required_fields]

            for field_name in required_field_names:
                if field_name not in config:
                    # Check if sts_id is provided (which can substitute for required fields)
                    if "sts_id" not in config:
                        errors.append(f"Required field '{field_name}' is missing")

            # Type validation for provided fields
            all_fields = {
                f.name: f
                for f in provider_info.required_fields + provider_info.optional_fields
            }
            for field_name, value in config.items():
                if field_name in all_fields:
                    field = all_fields[field_name]
                    validation_error = self._validate_field_value(field, value)
                    if validation_error:
                        errors.append(f"Field '{field_name}': {validation_error}")

        except Exception as e:
            errors.append(f"Validation error: {str(e)}")

        return ValidationResult(
            valid=len(errors) == 0, errors=errors, warnings=warnings
        )

    def _validate_field_value(self, field: ProviderField, value: Any) -> str | None:
        """Validate a field value against its constraints."""
        # Type validation
        if field.type == FieldType.STRING and not isinstance(value, str):
            return f"Expected string, got {type(value).__name__}"
        elif field.type == FieldType.INTEGER and not isinstance(value, int):
            return f"Expected integer, got {type(value).__name__}"
        elif field.type == FieldType.FLOAT and not isinstance(value, (int, float)):
            return f"Expected number, got {type(value).__name__}"
        elif field.type == FieldType.BOOLEAN and not isinstance(value, bool):
            return f"Expected boolean, got {type(value).__name__}"
        elif field.type == FieldType.LIST and not isinstance(value, list):
            return f"Expected list, got {type(value).__name__}"
        elif field.type == FieldType.DICT and not isinstance(value, dict):
            return f"Expected object, got {type(value).__name__}"

        # Range validation for numeric types
        if field.type in (FieldType.INTEGER, FieldType.FLOAT) and isinstance(
            value, (int, float)
        ):
            if field.min_value is not None and value < field.min_value:
                return f"Value {value} is below minimum {field.min_value}"
            if field.max_value is not None and value > field.max_value:
                return f"Value {value} is above maximum {field.max_value}"

        # Options validation
        if field.options and isinstance(value, str):
            if value not in field.options:
                return f"Value '{value}' not in allowed options: {field.options}"

        return None

    def expand_sts_id(self, provider_name: str, sts_id: str) -> Dict[str, Any]:
        """Expand an sts_id to full configuration using voice library."""
        # This will be implemented when we create the voice library service
        # For now, return empty dict
        return {}


# Global instance
provider_service = ProviderService()
