"""Voice library loading and expansion functionality."""

import logging
from pathlib import Path
from typing import Any, Dict, Optional, cast

import yaml

from ..tts_providers.base.exceptions import VoiceNotFoundError
from ..utils.logging import get_screenplay_logger
from .constants import REPO_VOICE_LIBRARY_PATH, USER_VOICE_LIBRARY_PATH

logger = get_screenplay_logger("voice_library.loader")


class VoiceLibrary:
    """Loads and manages voice library data."""

    def __init__(self) -> None:
        """
        Initialize the voice library.

        Loads voices from both project-level and user-level directories,
        with user-level voices overriding project-level ones for the same
        sts_id/provider combinations.
        """
        # Cache loaded voice data by provider
        self._voice_library_cache: Dict[str, Dict[str, Any]] = {}

    def _load_provider_voices(self, provider: str) -> Dict[str, Any]:
        """
        Load all voices for a specific provider from both project and user directories.

        User-level voices override project-level voices for the same sts_id.

        Args:
            provider: The TTS provider name

        Returns:
            Dict mapping voice IDs to voice data

        Raises:
            VoiceNotFoundError: If provider directory doesn't exist in either location
        """
        # Return cached data if available
        if provider in self._voice_library_cache:
            return self._voice_library_cache[provider]

        # Load voices from project directory first
        project_voices = self._load_voices_from_directory(
            REPO_VOICE_LIBRARY_PATH / provider, provider, "project"
        )

        # Load voices from user directory second (will override project voices)
        user_voices = self._load_voices_from_directory(
            USER_VOICE_LIBRARY_PATH / provider, provider, "user"
        )

        # Check if we found any voices at all
        if not project_voices and not user_voices:
            raise VoiceNotFoundError(
                f"No voice library found for provider '{provider}' in either "
                f"project ({REPO_VOICE_LIBRARY_PATH}) or user ({USER_VOICE_LIBRARY_PATH}) directories"
            )

        # Merge voices, with user voices overriding project voices
        all_voices = project_voices.copy()

        # Log any overrides
        for voice_id in user_voices:
            if voice_id in all_voices:
                logger.info(
                    f"User voice '{voice_id}' for provider '{provider}' overriding project voice"
                )
            all_voices[voice_id] = user_voices[voice_id]

        # Cache the merged voices
        self._voice_library_cache[provider] = all_voices
        return all_voices

    def _load_voices_from_directory(
        self, provider_dir: Path, provider: str, source: str
    ) -> Dict[str, Any]:
        """
        Load voices from a specific directory for a provider.

        Args:
            provider_dir: Directory containing voice files for the provider
            provider: The TTS provider name
            source: Source description ("project" or "user") for logging

        Returns:
            Dict mapping voice IDs to voice data

        Raises:
            ValueError: If duplicate voice IDs found within the same directory
        """
        if not provider_dir.exists() or not provider_dir.is_dir():
            return {}

        voices = {}

        # Load all YAML files in the provider directory
        for voice_file in provider_dir.glob("*.yaml"):
            if voice_file.name == "provider_schema.yaml":
                continue  # Skip schema files

            try:
                with open(voice_file, "r") as f:
                    data = yaml.safe_load(f)

                if data and isinstance(data, dict) and "voices" in data:
                    file_voices = data["voices"]
                    if isinstance(file_voices, dict):
                        # Check for duplicate voice IDs within this directory
                        for voice_id in file_voices:
                            if voice_id in voices:
                                logger.error(
                                    f"Duplicate voice ID '{voice_id}' found in {source} voice library "
                                    f"for provider '{provider}' in {voice_file}. "
                                    f"Voice already exists in {source} voice library."
                                )
                                raise ValueError(
                                    f"Duplicate voice ID '{voice_id}' found in {voice_file.name} "
                                    f"for provider '{provider}' in {source} voice library"
                                )
                        voices.update(file_voices)
                    else:
                        logger.warning(
                            f"Invalid voices section in {voice_file}: not a dictionary"
                        )

            except ValueError:
                # Re-raise ValueError (like duplicate voice IDs) immediately
                raise
            except Exception as e:
                logger.error(f"Error loading {voice_file}: {str(e)}")
                # Continue loading other files

        return voices

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
