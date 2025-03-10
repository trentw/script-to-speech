import io
import os
from unittest.mock import MagicMock, Mock, patch

import pytest

from tts_providers.base.tts_provider import TTSError, VoiceNotFoundError
from tts_providers.openai.tts_provider import OpenAITTSProvider


class TestOpenAITTSProvider:
    """Tests for the OpenAITTSProvider class."""

    def test_init(self):
        """Test initialization of the provider."""
        provider = OpenAITTSProvider()
        assert provider.client is None
        assert provider.speaker_configs == {}

    def test_validate_config_valid(self):
        """Test validate_speaker_config with valid configuration."""
        provider = OpenAITTSProvider()

        # Test with valid voice
        valid_config = {"voice": "alloy"}
        provider.validate_speaker_config(valid_config)  # Should not raise

        # Test with another valid voice
        valid_config = {"voice": "echo"}
        provider.validate_speaker_config(valid_config)  # Should not raise

    def test_validate_config_invalid_missing_voice(self):
        """Test validate_speaker_config with missing voice."""
        provider = OpenAITTSProvider()

        # Test with missing voice
        invalid_config = {}
        with pytest.raises(ValueError, match="Missing required field 'voice'"):
            provider.validate_speaker_config(invalid_config)

    def test_validate_config_invalid_voice_type(self):
        """Test validate_speaker_config with invalid voice type."""
        provider = OpenAITTSProvider()

        # Test with non-string voice
        invalid_config = {"voice": 123}
        with pytest.raises(ValueError, match="Field 'voice' must be a string"):
            provider.validate_speaker_config(invalid_config)

    def test_validate_config_invalid_voice_value(self):
        """Test validate_speaker_config with invalid voice value."""
        provider = OpenAITTSProvider()

        # Test with invalid voice value
        invalid_config = {"voice": "invalid_voice"}
        with pytest.raises(ValueError, match="Invalid voice 'invalid_voice'"):
            provider.validate_speaker_config(invalid_config)

    def test_initialize(self):
        """Test initialize method with valid configurations."""
        provider = OpenAITTSProvider()

        # Create valid speaker configs
        speaker_configs = {
            "default": {"voice": "alloy"},
            "BOB": {"voice": "echo"},
            "ALICE": {"voice": "nova"},
        }

        # Initialize the provider
        provider.initialize(speaker_configs)

        # Check that speaker configs were correctly stored
        assert len(provider.speaker_configs) == 3
        assert provider.speaker_configs["default"].voice == "alloy"
        assert provider.speaker_configs["BOB"].voice == "echo"
        assert provider.speaker_configs["ALICE"].voice == "nova"

    def test_initialize_with_invalid_config(self):
        """Test initialize method with invalid configuration."""
        provider = OpenAITTSProvider()

        # Create invalid speaker configs
        speaker_configs = {
            "default": {"voice": "alloy"},
            "INVALID": {"voice": "invalid_voice"},
        }

        # Initialize should raise for invalid voice
        with pytest.raises(ValueError, match="Invalid voice 'invalid_voice'"):
            provider.initialize(speaker_configs)

    def test_get_speaker_identifier(self):
        """Test get_speaker_identifier method."""
        provider = OpenAITTSProvider()

        # Initialize with sample configs
        provider.initialize(
            {
                "default": {"voice": "alloy"},
                "BOB": {"voice": "echo"},
            }
        )

        # Check identifiers include voice and model
        assert provider.get_speaker_identifier(None) == "alloy_tts-1-hd"
        assert provider.get_speaker_identifier("default") == "alloy_tts-1-hd"
        assert provider.get_speaker_identifier("BOB") == "echo_tts-1-hd"

    def test_get_speaker_identifier_not_found(self):
        """Test get_speaker_identifier with non-existent speaker."""
        provider = OpenAITTSProvider()

        # Initialize with only default
        provider.initialize({"default": {"voice": "alloy"}})

        # Should raise for unknown speaker
        with pytest.raises(VoiceNotFoundError):
            provider.get_speaker_identifier("NON_EXISTENT")

    def test_get_base_voice(self):
        """Test _get_base_voice method."""
        provider = OpenAITTSProvider()

        # Initialize with sample configs
        provider.initialize(
            {
                "default": {"voice": "alloy"},
                "BOB": {"voice": "echo"},
            }
        )

        # Check base voice names
        assert provider._get_base_voice(None) == "alloy"
        assert provider._get_base_voice("default") == "alloy"
        assert provider._get_base_voice("BOB") == "echo"

    def test_get_base_voice_not_found(self):
        """Test _get_base_voice with non-existent speaker."""
        provider = OpenAITTSProvider()

        # Initialize with only default
        provider.initialize({"default": {"voice": "alloy"}})

        # Should raise for unknown speaker
        with pytest.raises(VoiceNotFoundError):
            provider._get_base_voice("NON_EXISTENT")

    def test_get_speaker_configuration(self):
        """Test get_speaker_configuration method."""
        provider = OpenAITTSProvider()

        # Initialize with sample configs
        provider.initialize(
            {
                "default": {"voice": "alloy"},
                "BOB": {"voice": "echo"},
            }
        )

        # Check retrieved configs
        default_config = provider.get_speaker_configuration(None)
        assert default_config == {"voice": "alloy"}

        bob_config = provider.get_speaker_configuration("BOB")
        assert bob_config == {"voice": "echo"}

    def test_get_speaker_configuration_not_found(self):
        """Test get_speaker_configuration with non-existent speaker."""
        provider = OpenAITTSProvider()

        # Initialize with only default
        provider.initialize({"default": {"voice": "alloy"}})

        # Should raise for unknown speaker
        with pytest.raises(VoiceNotFoundError):
            provider.get_speaker_configuration("NON_EXISTENT")

    def test_get_provider_identifier(self):
        """Test get_provider_identifier class method."""
        # Check provider identifier
        assert OpenAITTSProvider.get_provider_identifier() == "openai"

    def test_get_yaml_instructions(self):
        """Test get_yaml_instructions class method."""
        # Check YAML instructions contain key information
        instructions = OpenAITTSProvider.get_yaml_instructions()
        assert "OPENAI_API_KEY" in instructions
        assert "voice:" in instructions
        assert "alloy" in instructions
        assert "echo" in instructions

    def test_get_required_fields(self):
        """Test get_required_fields class method."""
        # Check required fields
        required_fields = OpenAITTSProvider.get_required_fields()
        assert required_fields == ["voice"]

    def test_get_optional_fields(self):
        """Test get_optional_fields class method."""
        # Check optional fields
        optional_fields = OpenAITTSProvider.get_optional_fields()
        assert isinstance(optional_fields, list)

    def test_get_metadata_fields(self):
        """Test get_metadata_fields class method."""
        # Check metadata fields
        metadata_fields = OpenAITTSProvider.get_metadata_fields()
        assert isinstance(metadata_fields, list)

    @patch.dict(os.environ, {"OPENAI_API_KEY": "fake_api_key"})
    @patch("tts_providers.openai.tts_provider.OpenAI")
    def test_initialize_api_client(self, mock_openai):
        """Test _initialize_api_client method."""
        provider = OpenAITTSProvider()

        # Call initialize_api_client
        provider._initialize_api_client()

        # Check API was initialized with key
        mock_openai.assert_called_once_with(api_key="fake_api_key")
        assert provider.client is not None

    def test_initialize_api_client_missing_key(self, monkeypatch):
        """Test _initialize_api_client with missing API key."""
        # Ensure OPENAI_API_KEY is not set
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        provider = OpenAITTSProvider()

        # Should raise for missing API key
        with pytest.raises(
            TTSError, match="OPENAI_API_KEY environment variable is not set"
        ):
            provider._initialize_api_client()

    @patch.dict(os.environ, {"OPENAI_API_KEY": "fake_api_key"})
    @patch("tts_providers.openai.tts_provider.OpenAI")
    def test_initialize_api_client_error(self, mock_openai):
        """Test _initialize_api_client with initialization error."""
        # Make OpenAI constructor raise exception
        mock_openai.side_effect = Exception("API initialization failed")

        provider = OpenAITTSProvider()

        # Should raise for initialization error
        with pytest.raises(TTSError, match="Failed to initialize OpenAI client"):
            provider._initialize_api_client()

    @patch.dict(os.environ, {"OPENAI_API_KEY": "fake_api_key"})
    def test_generate_audio_success(self):
        """Test generate_audio method with successful generation."""
        # Create provider with pre-configured mock client
        provider = OpenAITTSProvider()
        provider.initialize({"default": {"voice": "alloy"}})

        # Create mock client and replace the real one
        mock_client = MagicMock()
        provider.client = mock_client

        # Setup mock response
        mock_response = MagicMock()
        mock_response.content = b"fake_audio_data"
        mock_client.audio.speech.create.return_value = mock_response

        # Generate audio
        audio_data = provider.generate_audio(None, "Test text")

        # Verify API was called correctly
        mock_client.audio.speech.create.assert_called_once_with(
            model=OpenAITTSProvider.MODEL, voice="alloy", input="Test text"
        )
        assert audio_data == b"fake_audio_data"

    @patch.dict(os.environ, {"OPENAI_API_KEY": "fake_api_key"})
    def test_generate_audio_with_speaker(self):
        """Test generate_audio method with specific speaker."""
        # Initialize provider with multiple speakers
        provider = OpenAITTSProvider()
        provider.initialize({"default": {"voice": "alloy"}, "BOB": {"voice": "echo"}})

        # Create mock client and replace the real one
        mock_client = MagicMock()
        provider.client = mock_client

        # Setup mock response
        mock_response = MagicMock()
        mock_response.content = b"fake_audio_data"
        mock_client.audio.speech.create.return_value = mock_response

        # Generate audio for specific speaker
        audio_data = provider.generate_audio("BOB", "Test text")

        # Verify API was called with correct voice
        mock_client.audio.speech.create.assert_called_once_with(
            model=OpenAITTSProvider.MODEL, voice="echo", input="Test text"
        )
        assert audio_data == b"fake_audio_data"

    @patch.dict(os.environ, {"OPENAI_API_KEY": "fake_api_key"})
    def test_generate_audio_auth_error(self):
        """Test generate_audio with authentication error."""
        # Initialize provider
        provider = OpenAITTSProvider()
        provider.initialize({"default": {"voice": "alloy"}})

        # Create mock client and replace the real one
        mock_client = MagicMock()
        provider.client = mock_client

        # Create a proper exception structure
        class MockAuthError(Exception):
            def __str__(self):
                return "Invalid API key"

        # Make API call raise authentication error
        mock_client.audio.speech.create.side_effect = MockAuthError()

        # Should raise TTSError for authentication error
        with pytest.raises(TTSError, match="Failed to generate audio"):
            provider.generate_audio(None, "Test text")

    @patch.dict(os.environ, {"OPENAI_API_KEY": "fake_api_key"})
    def test_generate_audio_rate_limit_error(self):
        """Test generate_audio with rate limit error."""
        # Initialize provider
        provider = OpenAITTSProvider()
        provider.initialize({"default": {"voice": "alloy"}})

        # Create mock client and replace the real one
        mock_client = MagicMock()
        provider.client = mock_client

        # Create a proper exception structure
        class MockRateLimitError(Exception):
            def __str__(self):
                return "Rate limit exceeded"

        # Make API call raise rate limit error
        mock_client.audio.speech.create.side_effect = MockRateLimitError()

        # Should raise TTSError for rate limit error
        with pytest.raises(TTSError, match="Failed to generate audio"):
            provider.generate_audio(None, "Test text")

    @patch.dict(os.environ, {"OPENAI_API_KEY": "fake_api_key"})
    def test_generate_audio_api_error(self):
        """Test generate_audio with API error."""
        # Initialize provider
        provider = OpenAITTSProvider()
        provider.initialize({"default": {"voice": "alloy"}})

        # Create mock client and replace the real one
        mock_client = MagicMock()
        provider.client = mock_client

        # Create a proper exception structure
        class MockAPIError(Exception):
            def __str__(self):
                return "API error"

        # Make API call raise API error
        mock_client.audio.speech.create.side_effect = MockAPIError()

        # Should raise TTSError for API error
        with pytest.raises(TTSError, match="Failed to generate audio"):
            provider.generate_audio(None, "Test text")

    @patch.dict(os.environ, {"OPENAI_API_KEY": "fake_api_key"})
    def test_generate_audio_generic_error(self):
        """Test generate_audio with generic error."""
        # Initialize provider
        provider = OpenAITTSProvider()
        provider.initialize({"default": {"voice": "alloy"}})

        # Create mock client and replace the real one
        mock_client = MagicMock()
        provider.client = mock_client

        # Make API call raise generic Exception
        mock_client.audio.speech.create.side_effect = Exception("Generic error")

        # Should raise TTSError for generic error
        with pytest.raises(TTSError, match="Failed to generate audio"):
            provider.generate_audio(None, "Test text")

    def test_is_empty_value(self):
        """Test _is_empty_value helper method."""
        provider = OpenAITTSProvider()

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
