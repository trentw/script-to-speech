import abc
from typing import Any, Dict

from .common_provider_mixin import TTSProviderCommonMixin  # Relative import


class StatefulTTSProviderBase(TTSProviderCommonMixin, abc.ABC):
    """Base class for stateful TTS providers."""

    def __init__(self) -> None:
        """
        Initialize stateful provider instance.

        This is a default implementation that does nothing.
        Subclasses should override this method to initialize their state.
        """
        pass

    @abc.abstractmethod
    def initialize(self) -> None:
        """Perform complex state setup (e.g., voice registries). Can be empty."""
        raise NotImplementedError

    @abc.abstractmethod
    def generate_audio(
        self, client: Any, speaker_config: Dict[str, Any], text: str
    ) -> bytes:
        """Generate audio using the client, config, and instance state."""
        raise NotImplementedError
