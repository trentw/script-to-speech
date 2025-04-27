import abc
from typing import Any, Dict

from .common_provider_mixin import TTSProviderCommonMixin  # Relative import


class StatefulTTSProviderBase(TTSProviderCommonMixin, abc.ABC):
    """Base class for stateful TTS providers."""

    def __init__(self) -> None:
        """
        Initialize stateful provider instance.

        Subclasses must perform all necessary state setup in this method,
        including complex operations like initializing voice registries.
        The provider instance should be fully ready to use after __init__ completes.
        """
        pass

    @abc.abstractmethod
    def generate_audio(
        self, client: Any, speaker_config: Dict[str, Any], text: str
    ) -> bytes:
        """Generate audio using the client, config, and instance state."""
        raise NotImplementedError
