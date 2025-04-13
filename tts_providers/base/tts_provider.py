import abc
from typing import Any, Dict, List, Optional


class TTSError(Exception):
    """Base exception class for TTS-related errors"""

    pass


class VoiceNotFoundError(TTSError):
    """Raised when a requested voice is not found"""

    pass


class TTSProvider(abc.ABC):
    @property
    @abc.abstractmethod
    def IS_STATEFUL(self) -> bool:
        """Declare whether the provider manages internal state beyond client."""
        raise NotImplementedError

    def __init__(self) -> None:
        """Initialize base provider, setting flag for setattr check."""
        self._initialized = True  # Flag to allow setting attributes during init

    def __setattr__(self, name: str, value: Any) -> None:
        """Prevent setting attributes on stateless providers after initialization."""
        # Allow setting attributes during __init__ or if _initialized exists
        if name == "_initialized" or not hasattr(self, "_initialized"):
            super().__setattr__(name, value)
        # If IS_STATEFUL is False, raise error if trying to set attributes after init
        elif not self.IS_STATEFUL:
            raise AttributeError(
                f"Cannot set attribute '{name}' on stateless provider "
                f"'{type(self).__name__}' after initialization."
            )
        else:
            super().__setattr__(name, value)

    @classmethod
    @abc.abstractmethod
    def instantiate_client(cls) -> Any:
        """Instantiate and return the API client for this provider."""
        pass

    def initialize(self) -> None:
        """
        Optional method for complex state setup in stateful providers
        (e.g., initializing helper classes like voice registries).
        """
        pass

    @abc.abstractmethod
    def generate_audio(
        self, client: Any, speaker_config: Dict[str, Any], text: str
    ) -> bytes:
        """
        Generate audio using the provided client and speaker config.

        Args:
            client: The initialized API client instance for this provider.
            speaker_config: The configuration dictionary for the specific speaker.
            text: The text to convert to speech.

        Returns:
            bytes: The generated audio data.

        Raises:
            TTSError: If audio generation fails.
        """
        pass

    @abc.abstractmethod
    def get_speaker_identifier(self, speaker_config: Dict[str, Any]) -> str:
        """
        Get the unique identifier for the voice defined in the speaker config.

        Args:
            speaker_config: The configuration dictionary for the specific speaker.

        Returns:
            str: The voice identifier (e.g., voice ID, model name).

        Raises:
            TTSError: If the identifier cannot be determined from the config.
        """
        pass

    @classmethod
    @abc.abstractmethod
    def get_provider_identifier(cls) -> str:
        """
        Get a unique identifier for this TTS provider.
        Provider directory name must match this identifier.

        Returns:
            str: Provider identifier (e.g., 'elevenlabs', 'openai')
        """
        pass

    @classmethod
    @abc.abstractmethod
    def get_yaml_instructions(cls) -> str:
        """
        Get instructions for configuring this provider in YAML.

        Returns:
            str: Instructions for configuring this provider
        """
        pass

    @classmethod
    @abc.abstractmethod
    def get_required_fields(cls) -> List[str]:
        """
        Get list of required configuration fields for this provider.

        Returns:
            List[str]: Names of required configuration fields
        """
        pass

    @classmethod
    @abc.abstractmethod
    def get_optional_fields(cls) -> List[str]:
        """
        Get list of optional configuration fields for this provider.

        Returns:
            List[str]: Names of optional configuration fields
        """
        pass

    @classmethod
    @abc.abstractmethod
    def get_metadata_fields(cls) -> List[str]:
        """
        Get list of metadata fields for this provider.

        Returns:
            List[str]: Names of metadata fields
        """
        pass

    @classmethod
    @abc.abstractmethod
    def validate_speaker_config(cls, speaker_config: Dict[str, Any]) -> None:
        """
        Validate speaker configuration for this provider.

        Args:
            speaker_config: Configuration dictionary for a speaker

        Raises:
            ValueError: If configuration is invalid, with detailed error message
        """
        pass
