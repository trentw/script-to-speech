import abc
from typing import Any, Dict, List


class TTSProviderCommonMixin(abc.ABC):
    @classmethod
    @abc.abstractmethod
    def get_provider_identifier(cls) -> str:
        """Get unique identifier (e.g., 'openai')."""
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def get_yaml_instructions(cls) -> str:
        """Get YAML configuration instructions."""
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def get_required_fields(cls) -> List[str]:
        """Get list of required config fields."""
        raise NotImplementedError

    @classmethod
    def get_optional_fields(cls) -> List[str]:
        """Get list of optional config fields. Default is empty list."""
        return []

    @classmethod
    def get_metadata_fields(cls) -> List[str]:
        """Get list of metadata fields. Default is empty list."""
        return []

    @classmethod
    @abc.abstractmethod
    def validate_speaker_config(cls, speaker_config: Dict[str, Any]) -> None:
        """Validate speaker config, raising ValueError if invalid."""
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def instantiate_client(cls) -> Any:
        """Instantiate and return the API client."""
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def get_speaker_identifier(cls, speaker_config: Dict[str, Any]) -> str:
        """Get unique voice identifier from config (e.g., voice ID + model)."""
        raise NotImplementedError

    @classmethod
    def get_max_download_threads(cls) -> int:
        """
        Get the max number of concurrent download threads for this provider.

        Each TTS provider has different rate limits and concurrency capabilities.
        This method allows each provider to specify how many concurrent API calls
        it can efficiently handle without triggering rate limits.

        Returns:
            int: The max number of concurrent threads for this provider.
                Default is 1
        """
        return 1
