from typing import Any, Dict

from ..base.stateless_tts_provider import StatelessTTSProviderBase
from ..dummy_common.mixin import DummyProviderMixin


class DummyStatelessTTSProvider(DummyProviderMixin, StatelessTTSProviderBase):
    """
    Dummy stateless TTS provider implementation.

    This provider inherits from:
    - DummyProviderMixin: For common dummy provider functionality
    - StatelessTTSProviderBase: For the stateless provider interface

    It provides a simple implementation that directly calls the backend's
    audio generation method without maintaining any state.
    """

    @classmethod
    def get_provider_identifier(cls) -> str:
        """Get the provider identifier."""
        return "dummy_stateless"

    @classmethod
    def generate_audio(
        cls, client: Any, speaker_config: Dict[str, Any], text: str
    ) -> bytes:
        """Generate audio using the client and config."""
        return cls._generate_dummy_audio(client, speaker_config, text)
