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
