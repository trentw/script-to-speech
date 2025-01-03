from abc import ABC, abstractmethod
from typing import Dict, Optional, List


class TTSError(Exception):
    """Base exception class for TTS-related errors"""
    pass


class VoiceNotFoundError(TTSError):
    """Raised when a requested voice is not found"""
    pass


class TTSProvider(ABC):
    """Base class for all TTS providers that defines the required interface."""

    @abstractmethod
    def initialize(self, config_path: Optional[str] = None) -> None:
        """
        Initialize the TTS provider with optional configuration.

        Args:
            config_path: Path to configuration file (optional)

        Raises:
            TTSError: If initialization fails
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
    def get_provider_identifier(self) -> str:
        """
        Get a unique identifier for this TTS provider.

        Returns:
            str: Provider identifier (e.g., 'elevenlabs', 'pyttsx3')
        """
        pass

    @staticmethod
    @abstractmethod
    def generate_yaml_config(chunks: List[Dict], output_path: str) -> None:
        """
        Generate a template YAML configuration file from processed chunks.

        Args:
            chunks: List of processed screenplay chunks
            output_path: Path where the YAML config should be saved

        Raises:
            TTSError: If YAML generation fails
        """
        pass
