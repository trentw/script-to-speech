import abc
from typing import Any, Dict

from .common_provider_mixin import TTSProviderCommonMixin  # Relative import


class StatelessTTSProviderBase(TTSProviderCommonMixin, abc.ABC):
    """Base class for stateless TTS providers."""

    @classmethod
    @abc.abstractmethod
    def generate_audio(
        cls, client: Any, speaker_config: Dict[str, Any], text: str
    ) -> bytes:
        """Generate audio using the client and config."""
        raise NotImplementedError
