import os
from unittest.mock import MagicMock, Mock, patch

import pytest

from tts_providers.base.tts_provider import TTSError, VoiceNotFoundError
from tts_providers.elevenlabs.tts_provider import ElevenLabsTTSProvider


class TestElevenLabsTTSProvider:
    """Tests for the ElevenLabsTTSProvider class."""

    def test_init(self):
        """Test initialization of the provider."""
        provider = ElevenLabsTTSProvider()
        assert provider.client is None
        assert provider.voice_registry_manager is None
        assert provider.speaker_configs == {}

    def test_validate_config_valid(self):
        """Test validate_speaker_config with valid configuration."""
        provider = ElevenLabsTTSProvider()

        # Test with valid voice
        valid_config = {"voice_id": "validVoiceId"}
        provider.validate_speaker_config(valid_config)  # Should not raise

    def test_validate_config_invalid_missing_voice(self):
        """Test validate_speaker_config with missing voice_id."""
        provider = ElevenLabsTTSProvider()

        # Test with missing voice_id
        invalid_config = {}
        with pytest.raises(ValueError, match="Missing required field 'voice_id'"):
            provider.validate_speaker_config(invalid_config)

    def test_validate_config_invalid_voice_type(self):
        """Test validate_speaker_config with invalid voice_id type."""
        provider = ElevenLabsTTSProvider()

        # Test with non-string voice_id
        invalid_config = {"voice_id": 123}
        with pytest.raises(ValueError, match="Field 'voice_id' must be a string"):
            provider.validate_speaker_config(invalid_config)

    def test_initialize(self):
        """Test initialize method with valid configurations."""
        provider = ElevenLabsTTSProvider()

        # Create valid speaker configs
        speaker_configs = {
            "default": {"voice_id": "voice1"},
            "BOB": {"voice_id": "voice2"},
            "ALICE": {"voice_id": "voice3"},
        }

        # Initialize the provider
        provider.initialize(speaker_configs)

        # Check that speaker configs were correctly stored
        assert len(provider.speaker_configs) == 3
        assert provider.speaker_configs["default"].voice_id == "voice1"
        assert provider.speaker_configs["BOB"].voice_id == "voice2"
        assert provider.speaker_configs["ALICE"].voice_id == "voice3"

    def test_initialize_with_invalid_config(self):
        """Test initialize method with invalid configuration."""
        provider = ElevenLabsTTSProvider()

        # Create invalid speaker configs
        speaker_configs = {
            "default": {"voice_id": "voice1"},
            "INVALID": {"voice_id": 123},  # Invalid voice_id type
        }

        # Initialize should raise for invalid voice_id
        # The implementation wraps the ValueError in a TTSError
        with pytest.raises(TTSError):
            provider.initialize(speaker_configs)

    def test_get_speaker_identifier(self):
        """Test get_speaker_identifier method."""
        provider = ElevenLabsTTSProvider()

        # Initialize with sample configs
        provider.initialize(
            {
                "default": {"voice_id": "voice1"},
                "BOB": {"voice_id": "voice2"},
            }
        )

        # Check identifiers
        assert provider.get_speaker_identifier(None) == "voice1"
        assert provider.get_speaker_identifier("default") == "voice1"
        assert provider.get_speaker_identifier("BOB") == "voice2"

    def test_get_speaker_identifier_not_found(self):
        """Test get_speaker_identifier with non-existent speaker."""
        provider = ElevenLabsTTSProvider()

        # Initialize with only default
        provider.initialize({"default": {"voice_id": "voice1"}})

        # Should raise for unknown speaker
        with pytest.raises(VoiceNotFoundError):
            provider.get_speaker_identifier("NON_EXISTENT")

    def test_get_speaker_configuration(self):
        """Test get_speaker_configuration method."""
        provider = ElevenLabsTTSProvider()

        # Initialize with sample configs
        provider.initialize(
            {
                "default": {"voice_id": "voice1"},
                "BOB": {"voice_id": "voice2"},
            }
        )

        # Check retrieved configs
        default_config = provider.get_speaker_configuration(None)
        assert default_config == {"voice_id": "voice1"}

        bob_config = provider.get_speaker_configuration("BOB")
        assert bob_config == {"voice_id": "voice2"}

    def test_get_speaker_configuration_not_found(self):
        """Test get_speaker_configuration with non-existent speaker."""
        provider = ElevenLabsTTSProvider()

        # Initialize with only default
        provider.initialize({"default": {"voice_id": "voice1"}})

        # Should raise for unknown speaker
        with pytest.raises(VoiceNotFoundError):
            provider.get_speaker_configuration("NON_EXISTENT")

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

    @patch.dict(os.environ, {"ELEVEN_API_KEY": "fake_api_key"})
    @patch("tts_providers.elevenlabs.tts_provider.ElevenLabs")
    @patch("tts_providers.elevenlabs.tts_provider.ElevenLabsVoiceRegistryManager")
    def test_initialize_api_client(self, mock_registry_manager, mock_elevenlabs):
        """Test _initialize_api_client method."""
        provider = ElevenLabsTTSProvider()

        # Call initialize_api_client
        provider._initialize_api_client()

        # Check API was initialized with key
        mock_elevenlabs.assert_called_once_with(api_key="fake_api_key")
        mock_registry_manager.assert_called_once_with("fake_api_key")
        assert provider.client is not None
        assert provider.voice_registry_manager is not None

    def test_initialize_api_client_missing_key(self, monkeypatch):
        """Test _initialize_api_client with missing API key."""
        # Ensure ELEVEN_API_KEY is not set
        monkeypatch.delenv("ELEVEN_API_KEY", raising=False)

        provider = ElevenLabsTTSProvider()

        # Should raise for missing API key
        with pytest.raises(
            TTSError, match="ELEVEN_API_KEY environment variable is not set"
        ):
            provider._initialize_api_client()

    @patch.dict(os.environ, {"ELEVEN_API_KEY": "fake_api_key"})
    @patch("tts_providers.elevenlabs.tts_provider.ElevenLabs")
    def test_initialize_api_client_error(self, mock_elevenlabs):
        """Test _initialize_api_client with initialization error."""
        # Make ElevenLabs constructor raise exception
        mock_elevenlabs.side_effect = Exception("API initialization failed")

        provider = ElevenLabsTTSProvider()

        # Should raise for initialization error
        with pytest.raises(TTSError, match="Failed to initialize ElevenLabs client"):
            provider._initialize_api_client()

    @patch.dict(os.environ, {"ELEVEN_API_KEY": "fake_api_key"})
    def test_generate_audio_success(self):
        """Test generate_audio method with successful generation."""
        # Create provider with pre-configured mock client
        provider = ElevenLabsTTSProvider()
        provider.initialize({"default": {"voice_id": "public_voice_id"}})

        # Create mock client and registry manager
        mock_client = MagicMock()
        mock_registry_manager = MagicMock()
        provider.client = mock_client
        provider.voice_registry_manager = mock_registry_manager

        # Setup mocks for successful execution
        mock_registry_manager.get_library_voice_id.return_value = "registry_voice_id"

        # Mock the response object
        mock_response = MagicMock()
        mock_response.__iter__.return_value = [b"chunk1", b"chunk2"]
        mock_client.text_to_speech.convert.return_value = mock_response

        # Generate audio
        audio_data = provider.generate_audio(None, "Test text")

        # Verify library voice ID was retrieved
        mock_registry_manager.get_library_voice_id.assert_called_once_with(
            "public_voice_id"
        )

        # Verify API was called correctly
        mock_client.text_to_speech.convert.assert_called_once()

        # Check call arguments - need to get the actual call args because there are many parameters
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
        """Test generate_audio method with specific speaker."""
        # Initialize provider with multiple speakers
        provider = ElevenLabsTTSProvider()
        provider.initialize(
            {
                "default": {"voice_id": "default_voice_id"},
                "BOB": {"voice_id": "bob_voice_id"},
            }
        )

        # Create mock client and registry manager
        mock_client = MagicMock()
        mock_registry_manager = MagicMock()
        provider.client = mock_client
        provider.voice_registry_manager = mock_registry_manager

        # Setup mocks for successful execution
        mock_registry_manager.get_library_voice_id.return_value = (
            "bob_registry_voice_id"
        )

        # Mock the response object
        mock_response = MagicMock()
        mock_response.__iter__.return_value = [b"chunk1", b"chunk2"]
        mock_client.text_to_speech.convert.return_value = mock_response

        # Generate audio for specific speaker
        audio_data = provider.generate_audio("BOB", "Test text")

        # Verify correct voice ID was used
        mock_registry_manager.get_library_voice_id.assert_called_once_with(
            "bob_voice_id"
        )

        call_args = mock_client.text_to_speech.convert.call_args[1]
        assert call_args["voice_id"] == "bob_registry_voice_id"

    @patch.dict(os.environ, {"ELEVEN_API_KEY": "fake_api_key"})
    def test_generate_audio_elevenlabs_error(self):
        """Test generate_audio with ElevenLabs API error."""
        # Initialize provider
        provider = ElevenLabsTTSProvider()
        provider.initialize({"default": {"voice_id": "voice_id"}})

        # Create mock client and registry manager
        mock_client = MagicMock()
        mock_registry_manager = MagicMock()
        provider.client = mock_client
        provider.voice_registry_manager = mock_registry_manager

        # Setup mocks for error case
        mock_registry_manager.get_library_voice_id.return_value = "registry_voice_id"
        mock_client.text_to_speech.convert.side_effect = Exception("API error")

        # Should raise TTSError for API error
        with pytest.raises(TTSError, match="Failed to generate audio"):
            provider.generate_audio(None, "Test text")

    @patch.dict(os.environ, {"ELEVEN_API_KEY": "fake_api_key"})
    def test_generate_audio_registry_error(self):
        """Test generate_audio with voice registry error."""
        # Initialize provider
        provider = ElevenLabsTTSProvider()
        provider.initialize({"default": {"voice_id": "voice_id"}})

        # Create mock client and registry manager
        mock_client = MagicMock()
        mock_registry_manager = MagicMock()
        provider.client = mock_client
        provider.voice_registry_manager = mock_registry_manager

        # Setup mocks for error case
        mock_registry_manager.get_library_voice_id.side_effect = RuntimeError(
            "Registry error"
        )

        # Should raise TTSError for registry error
        with pytest.raises(TTSError, match="Failed to generate audio"):
            provider.generate_audio(None, "Test text")

    def test_is_empty_value(self):
        """Test _is_empty_value helper method."""
        provider = ElevenLabsTTSProvider()

        # Test various empty values
        assert provider._is_empty_value(None) is True
        assert provider._is_empty_value("") is True
        assert provider._is_empty_value("  ") is True
        assert provider._is_empty_value([]) is True
        assert provider._is_empty_value({}) is True
        assert provider._is_empty_value(()) is True

        # Test non-empty values
        assert provider._is_empty_value("text") is False
        assert provider._is_empty_value(123) is False
        assert provider._is_empty_value([1, 2, 3]) is False
        assert provider._is_empty_value({"key": "value"}) is False
