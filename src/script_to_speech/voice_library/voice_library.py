"""Voice library loading and expansion functionality."""

import logging
from pathlib import Path
from typing import Any, Dict, Optional, cast

import yaml

from ..tts_providers.base.exceptions import VoiceNotFoundError
from ..utils.logging import get_screenplay_logger

logger = get_screenplay_logger("voice_library.loader")


class VoiceLibrary:
    """Loads and manages voice library data."""

    def __init__(self, library_root: Optional[Path] = None):
        """
        Initialize the voice library.

        Args:
            library_root: Root directory of voice library data.
                         Defaults to src/script_to_speech/voice_library_data
        """
        if library_root is None:
            # Default to voice_library_data in the same parent directory
            module_dir = Path(__file__).parent.parent
            library_root = module_dir / "voice_library_data"

        self.library_root = Path(library_root)
        # Cache loaded voice data by provider
        self._voice_library_cache: Dict[str, Dict[str, Any]] = {}

    def _load_provider_voices(self, provider: str) -> Dict[str, Any]:
        """
        Load all voices for a specific provider.

        Args:
            provider: The TTS provider name

        Returns:
            Dict mapping voice IDs to voice data

        Raises:
            VoiceNotFoundError: If provider directory doesn't exist
        """
        # Return cached data if available
        if provider in self._voice_library_cache:
            return self._voice_library_cache[provider]

        provider_dir = self.library_root / provider
        if not provider_dir.exists() or not provider_dir.is_dir():
            raise VoiceNotFoundError(
                f"No voice library found for provider '{provider}'"
            )

        all_voices = {}

        # Load all YAML files in the provider directory
        for voice_file in provider_dir.glob("*.yaml"):
            if voice_file.name == "provider_schema.yaml":
                continue  # Skip schema files

            try:
                with open(voice_file, "r") as f:
                    data = yaml.safe_load(f)

                if data and isinstance(data, dict) and "voices" in data:
                    voices = data["voices"]
                    if isinstance(voices, dict):
                        all_voices.update(voices)
                    else:
                        logger.warning(
                            f"Invalid voices section in {voice_file}: not a dictionary"
                        )

            except Exception as e:
                logger.error(f"Error loading {voice_file}: {str(e)}")
                # Continue loading other files

        # Cache the loaded voices
        self._voice_library_cache[provider] = all_voices
        return all_voices

    def expand_config(self, provider: str, sts_id: str) -> Dict[str, Any]:
        """
        Expand an sts_id to its full configuration.

        Args:
            provider: The TTS provider name
            sts_id: The voice identifier within that provider

        Returns:
            Dict containing the full config for that voice

        Raises:
            VoiceNotFoundError: If the provider/sts_id combination doesn't exist
        """
        # Validate inputs
        if not provider:
            raise ValueError("Provider cannot be empty")
        if not sts_id:
            raise VoiceNotFoundError(f"Voice ID cannot be empty")

        # Load provider's voice library
        try:
            provider_voices = self._load_provider_voices(provider)
        except VoiceNotFoundError:
            # Re-raise with more context
            raise VoiceNotFoundError(
                f"Cannot expand sts_id '{sts_id}': provider '{provider}' not found"
            )

        if sts_id not in provider_voices:
            available = list(provider_voices.keys())
            raise VoiceNotFoundError(
                f"Voice '{sts_id}' not found in {provider} voice library. "
                f"Available voices: {', '.join(available[:5])}"
                f"{' and more...' if len(available) > 5 else ''}"
            )

        voice_data = provider_voices[sts_id]

        # Extract and validate config section
        if "config" not in voice_data:
            raise ValueError(
                f"Voice '{sts_id}' in {provider} is missing 'config' section"
            )

        # Return a copy of the config
        config = cast(Dict[str, Any], voice_data["config"].copy())

        # Add provider field since we don't store it in voice library
        config["provider"] = provider

        return config
