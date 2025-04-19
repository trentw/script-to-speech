import unittest
from unittest.mock import MagicMock

from tts_providers.dummy_stateful.dummy_voice_registry_manager import (
    DummyVoiceRegistryManager,
)


class TestDummyVoiceRegistryManager(unittest.TestCase):
    """Tests for the DummyVoiceRegistryManager class."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_client = MagicMock()
        self.registry = DummyVoiceRegistryManager(self.mock_client)

    def test_initialization(self):
        """Test that the registry is initialized correctly."""
        self.assertEqual(self.registry.known_ids, set())
        self.assertIsNotNone(self.registry.lock)
        self.assertEqual(self.registry.backend_client, self.mock_client)

    def test_get_dummy_voice_id_empty(self):
        """Test getting a voice ID with an empty speaker ID."""
        # First call with empty ID
        voice_id = self.registry.get_dummy_voice_id("")
        self.assertEqual(voice_id, "dummy_default_stateful_voice")
        self.mock_client.simulate_lookup_delay.assert_called_with(True)

        # Known IDs should still be empty
        self.assertEqual(self.registry.known_ids, set())

    def test_get_dummy_voice_id_new(self):
        """Test getting a voice ID with a new speaker ID."""
        # First call with new ID
        voice_id = self.registry.get_dummy_voice_id("test_id")
        self.assertEqual(voice_id, "dummy_stateful_test_id")
        self.mock_client.simulate_lookup_delay.assert_called_with(True)

        # ID should now be in known_ids
        self.assertIn("test_id", self.registry.known_ids)

    def test_get_dummy_voice_id_existing(self):
        """Test getting a voice ID with an existing speaker ID."""
        # Add ID to known_ids
        self.registry.known_ids.add("test_id")

        # Call with existing ID
        voice_id = self.registry.get_dummy_voice_id("test_id")
        self.assertEqual(voice_id, "dummy_stateful_test_id")
        self.mock_client.simulate_lookup_delay.assert_called_with(False)

    def test_thread_safety(self):
        """Test that the registry uses locks for thread safety."""
        # This is a basic test to ensure the lock is used
        # A more comprehensive test would involve multiple threads

        # Create a mock lock
        mock_lock = MagicMock()
        self.registry.lock = mock_lock

        # Call get_dummy_voice_id
        self.registry.get_dummy_voice_id("test_id")

        # Verify lock was used
        mock_lock.__enter__.assert_called_once()
        mock_lock.__exit__.assert_called_once()


if __name__ == "__main__":
    unittest.main()
