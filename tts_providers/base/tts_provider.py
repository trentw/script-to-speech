from abc import ABC, abstractmethod
from typing import Dict, Optional, List, Any


class TTSError(Exception):
    """Base exception class for TTS-related errors"""

    pass


class VoiceNotFoundError(TTSError):
    """Raised when a requested voice is not found"""

    pass


class TTSProvider(ABC):
    @staticmethod
    def _is_empty_value(value: Any) -> bool:
        """Check if a value should be considered empty.

        Handles:
        - None
        - Empty string
        - Whitespace-only string
        - Empty collections
        """
        if value is None:
            return True
        if isinstance(value, str):
            return not value.strip()
        if isinstance(value, (list, dict, set, tuple)):
            return len(value) == 0
        return False

    @abstractmethod
    def initialize(self, speaker_configs: Dict[str, Dict[str, Any]]) -> None:
        """
        Initialize the TTS provider with speaker configurations.

        Args:
            speaker_configs: Dictionary mapping speaker names to their configurations.
                           Includes 'default' speaker if specified for this provider.

        Raises:
            TTSError: If initialization fails or configuration is invalid
        """
        pass

    @abstractmethod
    def generate_audio(self, speaker: Optional[str], text: str) -> bytes:
        """
        Generate audio for the given speaker and text.

        Args:
            speaker: The speaker to determine which voice to use, or None for default voice
            text: The text to convert to speech

        Returns:
            bytes: The generated audio data

        Raises:
            VoiceNotFoundError: If no voice is assigned to the speaker
            TTSError: If audio generation fails
        """
        pass

    @abstractmethod
    def get_speaker_identifier(self, speaker: Optional[str]) -> str:
        """
        Get the voice identifier for a given speaker.

        Args:
            speaker: The speaker to get the voice identifier for, or None for default voice

        Returns:
            str: The voice identifier for the speaker

        Raises:
            VoiceNotFoundError: If no voice is assigned to the speaker
        """
        pass

    @abstractmethod
    def get_speaker_configuration(self, speaker: Optional[str]) -> Dict[str, Any]:
        """
        Get the configuration parameters for a given speaker.

        Args:
            speaker: The speaker to get the configuration for, or None for default voice

        Returns:
            Dict[str, Any]: Configuration parameters that could be passed to initialize()

        Raises:
            VoiceNotFoundError: If no voice is assigned to the speaker
        """
        pass

    @classmethod
    @abstractmethod
    def get_provider_identifier(cls) -> str:
        """
        Get a unique identifier for this TTS provider.
        Provider directory name must match this identifier.

        Returns:
            str: Provider identifier (e.g., 'elevenlabs', 'openai')
        """
        pass

    @classmethod
    @abstractmethod
    def get_yaml_instructions(cls) -> str:
        """
        Get instructions for configuring this provider in YAML.

        Returns:
            str: Instructions for configuring this provider
        """
        pass

    @classmethod
    @abstractmethod
    def get_required_fields(cls) -> List[str]:
        """
        Get list of required configuration fields for this provider.

        Returns:
            List[str]: Names of required configuration fields
        """
        pass

    @classmethod
    @abstractmethod
    def get_optional_fields(cls) -> List[str]:
        """
        Get list of optional configuration fields for this provider.

        Returns:
            List[str]: Names of optional configuration fields
        """
        pass

    @classmethod
    @abstractmethod
    def get_metadata_fields(cls) -> List[str]:
        """
        Get list of metadata fields for this provider.

        Returns:
            List[str]: Names of metadata fields
        """
        pass

    @abstractmethod
    def validate_speaker_config(self, speaker_config: Dict[str, Any]) -> None:
        """
        Validate speaker configuration for this provider.

        Args:
            speaker_config: Configuration dictionary for a speaker

        Raises:
            ValueError: If configuration is invalid, with detailed error message
        """
        pass
