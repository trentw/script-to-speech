import time
import unittest
from unittest.mock import patch

from script_to_speech.dummy_tts_backend.backend import DummyTTSBackend


class TestDummyTTSBackend(unittest.TestCase):
    """Tests for the DummyTTSBackend class."""

    def setUp(self):
        """Set up test fixtures."""
        self.backend = DummyTTSBackend()
        self.client = self.backend.create_client()

    def test_client_creation(self):
        """Test that a client can be created from the backend."""
        self.assertIsNotNone(self.client)
        self.assertEqual(self.client.backend, self.backend)

    def test_audio_generation(self):
        """Test that audio can be generated with default parameters."""
        text = "Hello, world!"
        audio = self.client.generate_audio(text)
        self.assertEqual(audio, self.backend.dummy_audio_bytes)

    def test_silent_audio_generation(self):
        """Test that silent audio can be generated."""
        text = "Hello, world!"
        audio = self.client.generate_audio(text, generate_silent=True)
        self.assertEqual(audio, self.backend.silent_audio_bytes)

    def test_delay_calculation(self):
        """Test that delays are calculated correctly."""
        text = "Hello, world!"

        # Test with default parameters
        with patch("time.sleep") as mock_sleep:
            self.client.generate_audio(text)
            # Base delay + character delay
            expected_delay = 1.0 + (len(text) * 3.0 / 1000.0)
            mock_sleep.assert_called_once_with(expected_delay)

        # Test with custom request time
        with patch("time.sleep") as mock_sleep:
            self.client.generate_audio(text, request_time=0.5)
            expected_delay = 0.5 + (len(text) * 3.0 / 1000.0)
            mock_sleep.assert_called_once_with(expected_delay)

        # Test with additional delay
        with patch("time.sleep") as mock_sleep:
            self.client.generate_audio(text, additional_delay=0.3)
            expected_delay = 1.0 + (len(text) * 3.0 / 1000.0) + 0.3
            mock_sleep.assert_called_once_with(expected_delay)

        # Test with both custom request time and additional delay
        with patch("time.sleep") as mock_sleep:
            self.client.generate_audio(text, request_time=0.5, additional_delay=0.3)
            expected_delay = 0.5 + (len(text) * 3.0 / 1000.0) + 0.3
            mock_sleep.assert_called_once_with(expected_delay)

    def test_rate_limiting(self):
        """Test that rate limiting works correctly."""
        # This is a basic test to ensure the semaphore is used
        # A more comprehensive test would involve multiple threads

        # Create a mock semaphore
        mock_semaphore = unittest.mock.MagicMock()

        # Save the original semaphore
        original_semaphore = self.backend.rate_limiter

        try:
            # Replace the semaphore with our mock
            self.backend.rate_limiter = mock_semaphore

            # Call generate_audio
            self.client.generate_audio("Test")

            # Verify the semaphore was used as a context manager
            mock_semaphore.__enter__.assert_called_once()
            mock_semaphore.__exit__.assert_called_once()
        finally:
            # Restore the original semaphore
            self.backend.rate_limiter = original_semaphore

    def test_lookup_delay(self):
        """Test that lookup delays are simulated correctly."""
        # Test with new ID
        with patch("time.sleep") as mock_sleep:
            self.client.simulate_lookup_delay(True)
            mock_sleep.assert_called_once_with(self.backend.NEW_ID_LOOKUP_DELAY_SECONDS)

        # Test with existing ID
        with patch("time.sleep") as mock_sleep:
            self.client.simulate_lookup_delay(False)
            mock_sleep.assert_not_called()


if __name__ == "__main__":
    unittest.main()
