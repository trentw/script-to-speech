from typing import Any, Dict

from tts_providers.base.stateful_tts_provider import StatefulTTSProviderBase
from tts_providers.dummy_common.mixin import DummyProviderMixin
from tts_providers.dummy_stateful.dummy_voice_registry_manager import (
    DummyVoiceRegistryManager,
)


class DummyStatefulTTSProvider(DummyProviderMixin, StatefulTTSProviderBase):
    """
    Dummy stateful TTS provider implementation.

    This provider inherits from:
    - DummyProviderMixin: For common dummy provider functionality
    - StatefulTTSProviderBase: For the stateful provider interface

    It maintains state through a voice registry manager that simulates
    stateful operations like voice lookup/cloning delays.
    """

    @classmethod
    def get_provider_identifier(cls) -> str:
        """Get the provider identifier."""
        return "dummy_stateful"

    def __init__(self) -> None:
        """Initialize the provider with a voice registry manager."""
        super().__init__()

        # Create a separate client instance for the registry
        registry_backend_client = self.instantiate_client()

        # Initialize the voice registry manager
        self.voice_registry_manager = DummyVoiceRegistryManager(registry_backend_client)

    def generate_audio(
        self, client: Any, speaker_config: Dict[str, Any], text: str
    ) -> bytes:
        """
        Generate audio using the client, config, and instance state.

        This method:
        1. Gets the speaker ID from the config
        2. Simulates a stateful voice lookup operation
        3. Generates the audio using the common dummy provider logic
        """
        # Get the speaker ID from the config
        speaker_id = speaker_config.get("dummy_id", "")

        # Determine the ID to use for registry lookup
        id_for_registry = speaker_id if isinstance(speaker_id, str) else ""

        # Simulate stateful voice lookup (ignore return value, just for simulation)
        self.voice_registry_manager.get_dummy_voice_id(id_for_registry)

        # Generate the audio using the common dummy provider logic
        return self._generate_dummy_audio(client, speaker_config, text)
