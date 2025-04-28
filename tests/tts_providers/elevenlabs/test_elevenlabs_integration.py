import os
from collections import OrderedDict
from unittest.mock import MagicMock, Mock, call, patch

import pytest

from script_to_speech.tts_providers.base.exceptions import TTSError, VoiceNotFoundError
from script_to_speech.tts_providers.elevenlabs.tts_provider import ElevenLabsTTSProvider
from script_to_speech.tts_providers.elevenlabs.voice_registry_manager import (
    ElevenLabsVoiceRegistryManager,
)


class TestElevenLabsIntegration:
    """Integration tests for ElevenLabsTTSProvider and VoiceRegistryManager."""

    @patch.dict(os.environ, {"ELEVEN_API_KEY": "fake_api_key"})
    @patch("script_to_speech.tts_providers.elevenlabs.voice_registry_manager.ElevenLabs")
    @patch("script_to_speech.tts_providers.elevenlabs.tts_provider.ElevenLabs")
    def test_initialization_flow(self, mock_tts_client, mock_registry_client):
        """Test integration of provider initialization."""
        # Set up mocks for clients
        mock_tts_client_instance = MagicMock()
        mock_registry_client_instance = MagicMock()

        # Set mock return values
        mock_tts_client.return_value = mock_tts_client_instance
        mock_registry_client.return_value = mock_registry_client_instance

        # Create provider
        provider = ElevenLabsTTSProvider()

        # Verify provider is correctly configured
        assert provider.voice_registry_manager is not None

        # Verify ElevenLabs was called for the registry client
        mock_registry_client.assert_called_once_with(api_key="fake_api_key")

        # Mock the response for text_to_speech.convert
        mock_response = MagicMock()
        mock_response.__iter__.return_value = [b"audio_data"]
        mock_tts_client_instance.text_to_speech.convert.return_value = mock_response

        # Get client from the instantiate_client class method
        with patch(
            "script_to_speech.tts_providers.elevenlabs.tts_provider.ElevenLabsTTSProvider.instantiate_client",
            return_value=mock_tts_client_instance,
        ):
            # We also need to patch the voice registry manager's get_library_voice_id method
            with patch.object(
                provider.voice_registry_manager,
                "get_library_voice_id",
                return_value="registry_id",
            ):
                # Call generate_audio with the mocked client
                provider.generate_audio(
                    mock_tts_client_instance, {"voice_id": "default_voice_id"}, "Test"
                )

        # Verify text_to_speech.convert was called with the right parameters
        mock_tts_client_instance.text_to_speech.convert.assert_called_once()

    @patch.dict(os.environ, {"ELEVEN_API_KEY": "fake_api_key"})
    def test_voice_translation_flow(self):
        """Test integration of voice ID translation through registry manager."""
        # Create provider with mock components
        with patch(
            "script_to_speech.tts_providers.elevenlabs.tts_provider.ElevenLabsVoiceRegistryManager"
        ):
            provider = ElevenLabsTTSProvider()

            # Create mock client and override registry manager
            mock_client = MagicMock()
            mock_registry_manager = MagicMock()
            provider.voice_registry_manager = mock_registry_manager

            # Setup registry manager mocks
            mock_registry_manager.get_library_voice_id.side_effect = (
                lambda voice_id: f"registry_{voice_id}"
            )

            # Mock response for generate call
            mock_response = MagicMock()
            mock_response.__iter__.return_value = [b"audio_data"]
            mock_client.text_to_speech.convert.return_value = mock_response

            # Generate audio for a voice
            result = provider.generate_audio(
                mock_client, {"voice_id": "public_voice_id2"}, "Hello"
            )

            # Verify registry manager translated the public ID correctly
            mock_registry_manager.get_library_voice_id.assert_called_once_with(
                "public_voice_id2"
            )

            # Verify the correct registry ID was used for API call
            call_args = mock_client.text_to_speech.convert.call_args[1]
            assert call_args["voice_id"] == "registry_public_voice_id2"

            # Check result contains audio data
            assert result == b"audio_data"

    @patch.dict(os.environ, {"ELEVEN_API_KEY": "fake_api_key"})
    def test_lru_management_during_generation(self):
        """Test integration of LRU management during audio generation."""
        # Create provider with mock registry manager
        with patch(
            "script_to_speech.tts_providers.elevenlabs.tts_provider.ElevenLabsVoiceRegistryManager"
        ):
            provider = ElevenLabsTTSProvider()

            # Create mock client that returns audio data
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.__iter__.return_value = [b"audio_data"]
            mock_client.text_to_speech.convert.return_value = mock_response

            # Create registry manager with mock methods and override the one in provider
            registry_manager = MagicMock()
            # Set up the get_library_voice_id to return appropriate registry IDs
            registry_manager.get_library_voice_id.side_effect = (
                lambda voice_id: f"registry_{voice_id}"
            )
            provider.voice_registry_manager = registry_manager

            # Generate audio for each speaker in order: BOB, ALICE, default
            provider.generate_audio(
                mock_client, {"voice_id": "voice2"}, "Hello from Bob"
            )
            provider.generate_audio(
                mock_client, {"voice_id": "voice3"}, "Hello from Alice"
            )
            provider.generate_audio(
                mock_client, {"voice_id": "voice1"}, "Hello from default"
            )

            # Verify the registry manager was called with the correct IDs
            expected_calls = [call("voice2"), call("voice3"), call("voice1")]
            registry_manager.get_library_voice_id.assert_has_calls(expected_calls)

            # Verify the API calls used the correct registry IDs

    @patch.dict(os.environ, {"ELEVEN_API_KEY": "fake_api_key"})
    def test_voice_not_found_handling(self):
        """Test integration of voice not found error handling."""
        # Create provider with mock components
        with patch(
            "script_to_speech.tts_providers.elevenlabs.tts_provider.ElevenLabsVoiceRegistryManager"
        ):
            provider = ElevenLabsTTSProvider()

            # Create mock client and registry manager and override provider's registry manager
            mock_client = MagicMock()
            mock_registry_manager = MagicMock()
            mock_registry_manager.get_library_voice_id.side_effect = RuntimeError(
                "Voice not found"
            )
            provider.voice_registry_manager = mock_registry_manager

            # Generate audio should raise TTSError
            with pytest.raises(TTSError, match="Failed to generate audio"):
                provider.generate_audio(
                    mock_client, {"voice_id": "default_voice_id"}, "Hello"
                )

            # Verify registry manager was called
            mock_registry_manager.get_library_voice_id.assert_called_once_with(
                "default_voice_id"
            )

            # Verify client was not called due to registry error
            mock_client.text_to_speech.convert.assert_not_called()

    @patch.dict(os.environ, {"ELEVEN_API_KEY": "fake_api_key"})
    def test_full_registry_new_voice(self):
        """Test handling a full registry when adding a new voice."""
        # Create provider with mocked registry manager
        with patch(
            "script_to_speech.tts_providers.elevenlabs.tts_provider.ElevenLabsVoiceRegistryManager",
            return_value=None,
        ):
            provider = ElevenLabsTTSProvider()

            # Mock client to return audio data
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.__iter__.return_value = [b"audio_data"]
            mock_client.text_to_speech.convert.return_value = mock_response

            # Create registry manager with spies on key methods
            registry_manager = ElevenLabsVoiceRegistryManager("fake_api_key")
            registry_manager.client = MagicMock()
            registry_manager._make_room_in_registry = MagicMock()
            registry_manager._find_voice_owner = MagicMock(return_value="owner_id")
            registry_manager._add_voice_to_registry = MagicMock()

            # Set up registry with 30 voices (maximum limit)
            registry_manager.voice_registry = {}
            for i in range(30):
                registry_manager.voice_registry[f"voice{i}"] = (
                    f"registry_voice{i}",
                    "cloned",
                )

            # Initialize LRU tracking
            registry_manager.voice_usage_order = OrderedDict()
            for i in range(30):
                registry_manager.voice_usage_order[f"voice{i}"] = None

            registry_manager.is_initialized = True

            # After adding voice, update registry with new voice
            def add_voice_side_effect(*args):
                registry_manager.voice_registry["new_voice_id"] = (
                    "registry_new_voice",
                    "cloned",
                )

            registry_manager._add_voice_to_registry.side_effect = add_voice_side_effect

            # Override provider's registry manager
            provider.voice_registry_manager = registry_manager

            # Generate audio for new speaker
            provider.generate_audio(mock_client, {"voice_id": "new_voice_id"}, "Hello")

            # Verify room was made in registry
            registry_manager._make_room_in_registry.assert_called_once()

            # Verify voice owner was found
            registry_manager._find_voice_owner.assert_called_once_with("new_voice_id")

            # Verify voice was added to registry
            registry_manager._add_voice_to_registry.assert_called_once_with(
                "new_voice_id", "owner_id"
            )

            # Verify API call used correct registry ID
            call_args = mock_client.text_to_speech.convert.call_args[1]
            assert call_args["voice_id"] == "registry_new_voice"
