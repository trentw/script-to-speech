import unittest
from unittest.mock import MagicMock, patch

from script_to_speech.tts_providers.dummy_stateless.tts_provider import DummyStatelessTTSProvider


class TestDummyStatelessProvider(unittest.TestCase):
    """Tests for the DummyStatelessTTSProvider class."""

    def test_get_provider_identifier(self):
        """Test that the provider identifier is correct."""
        identifier = DummyStatelessTTSProvider.get_provider_identifier()
        self.assertEqual(identifier, "dummy_stateless")

    def test_generate_audio(self):
        """Test that audio generation works correctly."""
        # Create mock client
        mock_client = MagicMock()
        mock_client.generate_audio.return_value = b"test_audio"

        # Create mock config
        config = {"dummy_generate_silent": True}

        # Test text
        text = "Hello, world!"

        # Mock the _generate_dummy_audio method
        with patch.object(
            DummyStatelessTTSProvider,
            "_generate_dummy_audio",
            return_value=b"test_audio",
        ) as mock_generate:
            # Call generate_audio
            audio = DummyStatelessTTSProvider.generate_audio(mock_client, config, text)

            # Verify results
            self.assertEqual(audio, b"test_audio")
            mock_generate.assert_called_once_with(mock_client, config, text)


if __name__ == "__main__":
    unittest.main()
