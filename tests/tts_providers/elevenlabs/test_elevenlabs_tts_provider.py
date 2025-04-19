import os
from unittest.mock import MagicMock, Mock, patch

import pytest

from tts_providers.base.exceptions import TTSError, VoiceNotFoundError
from tts_providers.elevenlabs.tts_provider import ElevenLabsTTSProvider


class TestElevenLabsTTSProvider:
    """Tests for the ElevenLabsTTSProvider class."""

    def test_init(self):
        """Test initialization of the provider."""
        # Patch environment and registry manager to prevent actual initialization
        with patch.dict(os.environ, {"ELEVEN_API_KEY": "fake_api_key"}), patch(
            "tts_providers.elevenlabs.tts_provider.ElevenLabsVoiceRegistryManager"
        ):
            provider = ElevenLabsTTSProvider()

            # Verify it's a subclass of StatefulTTSProviderBase
            from tts_providers.base.stateful_tts_provider import StatefulTTSProviderBase

            assert isinstance(provider, StatefulTTSProviderBase)

            # Verify the voice_registry_manager is initialized
            assert provider.voice_registry_manager is not None

    def test_validate_config_valid(self):
        """Test validate_speaker_config with valid configuration."""
        # Test with valid voice (now a class method)
        valid_config = {"voice_id": "validVoiceId"}
        ElevenLabsTTSProvider.validate_speaker_config(valid_config)  # Should not raise

    def test_validate_config_invalid_missing_voice(self):
        """Test validate_speaker_config with missing voice_id."""
        # Test with missing voice_id (now a class method)
        invalid_config = {}
        with pytest.raises(ValueError, match="Missing required field 'voice_id'"):
            ElevenLabsTTSProvider.validate_speaker_config(invalid_config)

    def test_validate_config_invalid_voice_type(self):
        """Test validate_speaker_config with invalid voice_id type."""
        # Test with non-string voice_id (now a class method)
        invalid_config = {"voice_id": 123}
        with pytest.raises(ValueError, match="Field 'voice_id' must be a string"):
            ElevenLabsTTSProvider.validate_speaker_config(invalid_config)

    @patch.dict(os.environ, {"ELEVEN_API_KEY": "fake_api_key"})
    @patch("tts_providers.elevenlabs.tts_provider.ElevenLabsVoiceRegistryManager")
    def test_initialization_in_constructor(self, mock_registry_manager):
        """Test registry manager is initialized in constructor."""
        # Initialize provider
        provider = ElevenLabsTTSProvider()

        # Check voice registry manager was created
        assert provider.voice_registry_manager is not None
        mock_registry_manager.assert_called_once()

    @patch.dict(os.environ, {})
    @patch(
        "tts_providers.elevenlabs.tts_provider.ElevenLabsVoiceRegistryManager",
        side_effect=TTSError("ELEVEN_API_KEY environment variable is not set"),
    )
    def test_constructor_missing_key(self, mock_registry_manager):
        """Test constructor with missing API key."""
        # Should raise for missing API key
        with pytest.raises(
            TTSError, match="ELEVEN_API_KEY environment variable is not set"
        ):
            provider = ElevenLabsTTSProvider()

    @patch.dict(os.environ, {"ELEVEN_API_KEY": "fake_api_key"})
    @patch(
        "tts_providers.elevenlabs.tts_provider.ElevenLabsVoiceRegistryManager",
        side_effect=Exception("Registry initialization failed"),
    )
    def test_constructor_error(self, mock_registry_manager):
        """Test constructor with error creating registry manager."""
        # Should raise for registry manager error
        with pytest.raises(
            TTSError,
            match="Failed to initialize ElevenLabsVoiceRegistryManager: Registry initialization failed",
        ):
            provider = ElevenLabsTTSProvider()

    @patch.dict(os.environ, {"ELEVEN_API_KEY": "fake_api_key"})
    @patch("tts_providers.elevenlabs.tts_provider.ElevenLabs")
    def test_instantiate_client(self, mock_elevenlabs):
        """Test instantiate_client class method."""
        # Call the class method
        client = ElevenLabsTTSProvider.instantiate_client()

        # Verify the client was created correctly
        mock_elevenlabs.assert_called_once_with(api_key="fake_api_key")
        assert client is not None

    @patch.dict(os.environ, {})
    @patch("tts_providers.elevenlabs.tts_provider.ElevenLabs")
    def test_instantiate_client_missing_key(self, mock_elevenlabs):
        """Test instantiate_client with missing API key."""
        # Mock the elevenlabs client to raise proper error
        mock_elevenlabs.side_effect = TTSError(
            "ELEVEN_API_KEY environment variable is not set"
        )

        # Should raise for missing API key
        with pytest.raises(
            TTSError, match="ELEVEN_API_KEY environment variable is not set"
        ):
            ElevenLabsTTSProvider.instantiate_client()

    @patch.dict(os.environ, {"ELEVEN_API_KEY": "fake_api_key"})
    @patch("tts_providers.elevenlabs.tts_provider.ElevenLabsVoiceRegistryManager")
    def test_get_speaker_identifier(self, mock_registry_manager):
        """Test get_speaker_identifier method."""
        # Initialize provider with mocked dependencies
        provider = ElevenLabsTTSProvider()

        # Test with direct config dictionary
        speaker_config = {"voice_id": "voice1"}

        # Call get_speaker_identifier with config
        voice_id = provider.get_speaker_identifier(speaker_config)

        # Verify it returns the voice_id from the config
        assert voice_id == "voice1"

    # get_speaker_configuration method has been removed from provider and moved to TTSProviderManager

    def test_get_provider_identifier(self):
        """Test get_provider_identifier class method."""
        # Check provider identifier
        assert ElevenLabsTTSProvider.get_provider_identifier() == "elevenlabs"

    def test_get_yaml_instructions(self):
        """Test get_yaml_instructions class method."""
        # Check YAML instructions contain key information
        instructions = ElevenLabsTTSProvider.get_yaml_instructions()
        assert "ELEVEN_API_KEY" in instructions
        assert "voice_id:" in instructions

    def test_get_required_fields(self):
        """Test get_required_fields class method."""
        # Check required fields
        required_fields = ElevenLabsTTSProvider.get_required_fields()
        assert required_fields == ["voice_id"]

    def test_get_optional_fields(self):
        """Test get_optional_fields class method."""
        # Check optional fields
        optional_fields = ElevenLabsTTSProvider.get_optional_fields()
        assert isinstance(optional_fields, list)

    def test_get_metadata_fields(self):
        """Test get_metadata_fields class method."""
        # Check metadata fields
        metadata_fields = ElevenLabsTTSProvider.get_metadata_fields()
        assert isinstance(metadata_fields, list)

    # _initialize_api_client method has been replaced by instantiate_client class method and initialize instance method

    @patch.dict(os.environ, {"ELEVEN_API_KEY": "fake_api_key"})
    def test_generate_audio_success(self):
        """Test generate_audio method with successful generation."""
        provider = ElevenLabsTTSProvider()

        # Create mock client
        mock_client = MagicMock()

        # Create mock voice registry manager and set it on the provider
        mock_registry_manager = MagicMock()
        provider.voice_registry_manager = mock_registry_manager

        # Create speaker config
        speaker_config = {"voice_id": "public_voice_id"}

        # Setup mocks for successful execution
        mock_registry_manager.get_library_voice_id.return_value = "registry_voice_id"

        # Mock the response object
        mock_response = MagicMock()
        mock_response.__iter__.return_value = [b"chunk1", b"chunk2"]
        mock_client.text_to_speech.convert.return_value = mock_response

        # Generate audio with passed client and config
        audio_data = provider.generate_audio(mock_client, speaker_config, "Test text")

        # Verify library voice ID was retrieved
        mock_registry_manager.get_library_voice_id.assert_called_once_with(
            "public_voice_id"
        )

        # Verify API was called correctly
        mock_client.text_to_speech.convert.assert_called_once()

        # Check call arguments
        call_args = mock_client.text_to_speech.convert.call_args[1]
        assert call_args["voice_id"] == "registry_voice_id"
        assert call_args["text"] == "Test text"
        assert call_args["optimize_streaming_latency"] == "0"
        assert call_args["output_format"] == "mp3_44100_192"
        assert call_args["model_id"] == "eleven_multilingual_v2"

        # Check the audio data was concatenated correctly
        assert audio_data == b"chunk1chunk2"

    @patch.dict(os.environ, {"ELEVEN_API_KEY": "fake_api_key"})
    def test_generate_audio_with_specific_speaker(self):
        """Test generate_audio method with specific speaker configuration."""
        provider = ElevenLabsTTSProvider()

        # Create mock client
        mock_client = MagicMock()

        # Create mock voice registry manager and set it on the provider
        mock_registry_manager = MagicMock()
        provider.voice_registry_manager = mock_registry_manager

        # Create speaker config for a specific speaker
        speaker_config = {"voice_id": "bob_voice_id"}

        # Setup mocks for successful execution
        mock_registry_manager.get_library_voice_id.return_value = (
            "bob_registry_voice_id"
        )

        # Mock the response object
        mock_response = MagicMock()
        mock_response.__iter__.return_value = [b"chunk1", b"chunk2"]
        mock_client.text_to_speech.convert.return_value = mock_response

        # Generate audio with passed client and specific config
        audio_data = provider.generate_audio(mock_client, speaker_config, "Test text")

        # Verify correct voice ID was used
        mock_registry_manager.get_library_voice_id.assert_called_once_with(
            "bob_voice_id"
        )

        call_args = mock_client.text_to_speech.convert.call_args[1]
        assert call_args["voice_id"] == "bob_registry_voice_id"

    @patch.dict(os.environ, {"ELEVEN_API_KEY": "fake_api_key"})
    def test_generate_audio_elevenlabs_error(self):
        """Test generate_audio with ElevenLabs API error."""
        provider = ElevenLabsTTSProvider()

        # Create mock client
        mock_client = MagicMock()

        # Create mock voice registry manager and set it on the provider
        mock_registry_manager = MagicMock()
        provider.voice_registry_manager = mock_registry_manager

        # Create speaker config
        speaker_config = {"voice_id": "voice_id"}

        # Setup mocks for error case
        mock_registry_manager.get_library_voice_id.return_value = "registry_voice_id"
        mock_client.text_to_speech.convert.side_effect = Exception("API error")

        # Should raise TTSError for API error
        with pytest.raises(TTSError, match="Failed to generate audio"):
            provider.generate_audio(mock_client, speaker_config, "Test text")

    @patch.dict(os.environ, {"ELEVEN_API_KEY": "fake_api_key"})
    def test_generate_audio_registry_error(self):
        """Test generate_audio with voice registry error."""
        provider = ElevenLabsTTSProvider()

        # Create mock client
        mock_client = MagicMock()

        # Create mock voice registry manager and set it on the provider
        mock_registry_manager = MagicMock()
        provider.voice_registry_manager = mock_registry_manager

        # Create speaker config
        speaker_config = {"voice_id": "voice_id"}

        # Setup mocks for error case
        mock_registry_manager.get_library_voice_id.side_effect = RuntimeError(
            "Registry error"
        )

        # Should raise TTSError for registry error
        with pytest.raises(TTSError, match="Failed to generate audio"):
            provider.generate_audio(mock_client, speaker_config, "Test text")

    # The _is_empty_value method has been removed in the refactoring
