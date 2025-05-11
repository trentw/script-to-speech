import threading
from typing import Any, Set


class DummyVoiceRegistryManager:
    """
    Dummy voice registry manager for the stateful provider.

    This class simulates the behavior of a voice registry system like the one
    used by ElevenLabs, including:
    - Tracking known voice IDs
    - Thread-safe operations
    - Simulating lookup delays for new vs. existing voices
    """

    def __init__(self, backend_client: Any) -> None:
        """
        Initialize the dummy voice registry manager.

        Args:
            backend_client: The backend client to use for simulating delays
        """
        self.backend_client = backend_client
        self.known_ids: Set[str] = set()
        self.lock = threading.Lock()

    def get_dummy_voice_id(self, speaker_id_or_empty: str) -> str:
        """
        Get a dummy voice ID, simulating the behavior of a voice registry.

        This method:
        1. Determines if this is a new or existing voice ID
        2. Simulates appropriate lookup delays
        3. Tracks known IDs for future lookups

        Args:
            speaker_id_or_empty: The speaker ID to look up, or empty string for default

        Returns:
            str: A dummy voice ID for use with the API
        """
        with self.lock:
            # Determine if this is a new ID
            is_new = (
                not speaker_id_or_empty or speaker_id_or_empty not in self.known_ids
            )

            # Generate the appropriate result ID
            if not speaker_id_or_empty:
                result_id = "dummy_default_stateful_voice"
            elif is_new:
                # Add to known IDs for future lookups
                self.known_ids.add(speaker_id_or_empty)
                result_id = f"dummy_stateful_{speaker_id_or_empty}"
            else:
                result_id = f"dummy_stateful_{speaker_id_or_empty}"

            # Simulate lookup delay based on whether this is a new ID
            self.backend_client.simulate_lookup_delay(is_new)

            return result_id
