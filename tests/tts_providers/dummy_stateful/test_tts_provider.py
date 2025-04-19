import unittest
from unittest.mock import MagicMock, patch

from tts_providers.dummy_stateful.tts_provider import DummyStatefulTTSProvider


class TestDummyStatefulTTSProvider(unittest.TestCase):
    """Tests for the DummyStatefulTTSProvider class."""

    def test_get_provider_identifier(self):
        """Test that the provider identifier is correct."""
        identifier = DummyStatefulTTSProvider.get_provider_identifier()
        self.assertEqual(identifier, "dummy_stateful")

    def test_initialization(self):
        """Test that the provider is initialized correctly."""
        # Mock the instantiate_client method
        with patch.object(
            DummyStatefulTTSProvider, "instantiate_client", return_value="mock_client"
        ) as mock_instantiate:
            # Mock the DummyVoiceRegistryManager
            with patch(
                "tts_providers.dummy_stateful.tts_provider.DummyVoiceRegistryManager"
            ) as mock_registry_class:
                # Create provider instance
                provider = DummyStatefulTTSProvider()

                # Verify client was instantiated
                mock_instantiate.assert_called_once()

                # Verify registry was created with client
                mock_registry_class.assert_called_once_with("mock_client")

                # Verify registry was stored
                self.assertEqual(
                    provider.voice_registry_manager, mock_registry_class.return_value
                )

    def test_generate_audio(self):
        """Test that audio generation works correctly."""
        # Create mock client
        mock_client = MagicMock()

        # Create mock config with ID
        config = {"id": "test_id"}

        # Create mock registry manager
        mock_registry = MagicMock()

        # Create provider instance with mock registry
        provider = DummyStatefulTTSProvider()
        provider.voice_registry_manager = mock_registry

        # Mock the _generate_dummy_audio method
        with patch.object(
            provider, "_generate_dummy_audio", return_value=b"test_audio"
        ) as mock_generate:
            # Call generate_audio
            audio = provider.generate_audio(mock_client, config, "test text")

            # Verify registry was called
            mock_registry.get_dummy_voice_id.assert_called_once_with("test_id")

            # Verify audio was generated
            mock_generate.assert_called_once_with(mock_client, config, "test text")

            # Verify result
            self.assertEqual(audio, b"test_audio")

    def test_generate_audio_no_id(self):
        """Test audio generation with no ID in config."""
        # Create mock client
        mock_client = MagicMock()

        # Create mock config without ID
        config = {}

        # Create mock registry manager
        mock_registry = MagicMock()

        # Create provider instance with mock registry
        provider = DummyStatefulTTSProvider()
        provider.voice_registry_manager = mock_registry

        # Mock the _generate_dummy_audio method
        with patch.object(
            provider, "_generate_dummy_audio", return_value=b"test_audio"
        ) as mock_generate:
            # Call generate_audio
            audio = provider.generate_audio(mock_client, config, "test text")

            # Verify registry was called with empty string
            mock_registry.get_dummy_voice_id.assert_called_once_with("")

            # Verify audio was generated
            mock_generate.assert_called_once_with(mock_client, config, "test text")

            # Verify result
            self.assertEqual(audio, b"test_audio")


if __name__ == "__main__":
    unittest.main()
