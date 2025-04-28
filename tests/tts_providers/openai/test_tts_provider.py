import io
import os
from unittest.mock import MagicMock, Mock, patch

import pytest
from openai import APIError, AuthenticationError, RateLimitError

from script_to_speech.tts_providers.base.exceptions import TTSError, VoiceNotFoundError
from script_to_speech.tts_providers.openai.tts_provider import OpenAITTSProvider


class TestOpenAITTSProvider:
    """Tests for the OpenAITTSProvider class."""

    def test_init(self):
        """Test initialization of the provider."""
        # No need to instantiate stateless providers
        # Just verify it's a subclass of StatelessTTSProviderBase
        from script_to_speech.tts_providers.base.stateless_tts_provider import StatelessTTSProviderBase

        assert issubclass(OpenAITTSProvider, StatelessTTSProviderBase)

    def test_validate_config_valid(self):
        """Test validate_speaker_config with valid configuration."""
        # Test with valid voice (now a class method)
        valid_config = {"voice": "alloy"}
        OpenAITTSProvider.validate_speaker_config(valid_config)  # Should not raise

        # Test with another valid voice
        valid_config = {"voice": "echo"}
        OpenAITTSProvider.validate_speaker_config(valid_config)  # Should not raise

    def test_validate_config_invalid_missing_voice(self):
        """Test validate_speaker_config with missing voice."""
        # Test with missing voice (now a class method)
        invalid_config = {}
        with pytest.raises(ValueError, match="Missing required field 'voice'"):
            OpenAITTSProvider.validate_speaker_config(invalid_config)

    def test_validate_config_invalid_voice_type(self):
        """Test validate_speaker_config with invalid voice type."""
        # Test with non-string voice (now a class method)
        invalid_config = {"voice": 123}
        with pytest.raises(ValueError, match="Field 'voice' must be a string"):
            OpenAITTSProvider.validate_speaker_config(invalid_config)

    def test_validate_config_invalid_voice_value(self):
        """Test validate_speaker_config with invalid voice value."""
        # Test with invalid voice value (now a class method)
        invalid_config = {"voice": "invalid_voice"}
        with pytest.raises(ValueError, match="Invalid voice 'invalid_voice'"):
            OpenAITTSProvider.validate_speaker_config(invalid_config)

    def test_no_initialize_method(self):
        """Test that stateless providers don't have initialize method."""
        provider = OpenAITTSProvider()

        # Stateless providers should not have initialize method
        assert not hasattr(provider, "initialize")

    def test_instantiate_client(self):
        """Test instantiate_client class method."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "fake_api_key"}):
            # Call the class method
            client = OpenAITTSProvider.instantiate_client()

            # Verify we got a client back
            assert client is not None

    def test_get_speaker_identifier(self):
        """Test get_speaker_identifier method."""
        provider = OpenAITTSProvider()

        # Test with direct config dictionaries instead of stored speaker configs
        # Check identifiers include voice and model
        assert provider.get_speaker_identifier({"voice": "alloy"}) == "alloy_tts-1-hd"
        assert provider.get_speaker_identifier({"voice": "echo"}) == "echo_tts-1-hd"
        assert provider.get_speaker_identifier({"voice": "nova"}) == "nova_tts-1-hd"

    def test_get_speaker_identifier_invalid(self):
        """Test get_speaker_identifier with invalid config."""
        provider = OpenAITTSProvider()

        # Should raise for missing voice
        with pytest.raises(TTSError):
            provider.get_speaker_identifier({})

        # Should raise for invalid voice type
        with pytest.raises(TTSError):
            provider.get_speaker_identifier({"voice": 123})

        # Should raise for invalid voice
        with pytest.raises(VoiceNotFoundError):
            provider.get_speaker_identifier({"voice": "invalid_voice"})

    def test_get_voice_from_config(self):
        """Test _get_voice_from_config method."""
        provider = OpenAITTSProvider()

        # Test with direct config dictionaries
        assert provider._get_voice_from_config({"voice": "alloy"}) == "alloy"
        assert provider._get_voice_from_config({"voice": "echo"}) == "echo"
        assert provider._get_voice_from_config({"voice": "nova"}) == "nova"

    def test_get_voice_from_config_invalid(self):
        """Test _get_voice_from_config with invalid config."""
        provider = OpenAITTSProvider()

        # Should raise for missing voice
        with pytest.raises(TTSError):
            provider._get_voice_from_config({})

        # Should raise for non-string voice
        with pytest.raises(TTSError):
            provider._get_voice_from_config({"voice": 123})

        # Should raise for invalid voice
        with pytest.raises(VoiceNotFoundError):
            provider._get_voice_from_config({"voice": "invalid_voice"})

    # get_speaker_configuration method has been removed from provider and moved to TTSProviderManager

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
    @patch("script_to_speech.tts_providers.openai.tts_provider.OpenAI")
    def test_instantiate_client(self, mock_openai):
        """Test instantiate_client class method."""
        # Call instantiate_client
        client = OpenAITTSProvider.instantiate_client()

        # Check API was initialized with key
        mock_openai.assert_called_once_with(api_key="fake_api_key")
        assert client is not None

    def test_instantiate_client_missing_key(self, monkeypatch):
        """Test instantiate_client with missing API key."""
        # Ensure OPENAI_API_KEY is not set
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        # Should raise for missing API key
        with pytest.raises(
            TTSError, match="OPENAI_API_KEY environment variable is not set"
        ):
            OpenAITTSProvider.instantiate_client()

    @patch.dict(os.environ, {"OPENAI_API_KEY": "fake_api_key"})
    @patch("script_to_speech.tts_providers.openai.tts_provider.OpenAI")
    def test_instantiate_client_error(self, mock_openai):
        """Test instantiate_client with initialization error."""
        # Make OpenAI constructor raise exception
        mock_openai.side_effect = Exception("API initialization failed")

        # Should raise for initialization error
        with pytest.raises(TTSError, match="Failed to initialize OpenAI client"):
            OpenAITTSProvider.instantiate_client()

    @patch.dict(os.environ, {"OPENAI_API_KEY": "fake_api_key"})
    def test_generate_audio_success(self):
        """Test generate_audio method with successful generation."""
        provider = OpenAITTSProvider()

        # Create mock client
        mock_client = MagicMock()

        # Setup mock response
        mock_response = MagicMock()
        mock_response.content = b"fake_audio_data"
        mock_client.audio.speech.create.return_value = mock_response

        # Create speaker config
        speaker_config = {"voice": "alloy"}

        # Generate audio with passed client and config instead of stored ones
        audio_data = provider.generate_audio(mock_client, speaker_config, "Test text")

        # Verify API was called correctly
        mock_client.audio.speech.create.assert_called_once_with(
            model=OpenAITTSProvider.MODEL, voice="alloy", input="Test text"
        )
        assert audio_data == b"fake_audio_data"

    @patch.dict(os.environ, {"OPENAI_API_KEY": "fake_api_key"})
    def test_generate_audio_different_voice(self):
        """Test generate_audio method with different voice."""
        provider = OpenAITTSProvider()

        # Create mock client
        mock_client = MagicMock()

        # Setup mock response
        mock_response = MagicMock()
        mock_response.content = b"fake_audio_data"
        mock_client.audio.speech.create.return_value = mock_response

        # Create speaker config with a different voice
        speaker_config = {"voice": "echo"}

        # Generate audio with the specified voice
        audio_data = provider.generate_audio(mock_client, speaker_config, "Test text")

        # Verify API was called with correct voice
        mock_client.audio.speech.create.assert_called_once_with(
            model=OpenAITTSProvider.MODEL, voice="echo", input="Test text"
        )
        assert audio_data == b"fake_audio_data"

    @patch.dict(os.environ, {"OPENAI_API_KEY": "fake_api_key"})
    def test_generate_audio_client_none(self):
        """Test generate_audio with None client."""
        provider = OpenAITTSProvider()

        # Generate audio with None client should raise error
        with pytest.raises(TTSError, match="OpenAI client is not initialized"):
            provider.generate_audio(None, {"voice": "alloy"}, "Test text")

    @patch.dict(os.environ, {"OPENAI_API_KEY": "fake_api_key"})
    def test_generate_audio_auth_error(self):
        """Test generate_audio with authentication error."""
        provider = OpenAITTSProvider()

        # Create mock client
        mock_client = MagicMock()

        # Create speaker config
        speaker_config = {"voice": "alloy"}

        # Create a proper exception structure for AuthenticationError
        class MockAuthError(Exception):
            def __str__(self):
                return "Invalid API key"

        # Make API call raise authentication error
        mock_client.audio.speech.create.side_effect = MockAuthError()

        # Should raise TTSError for authentication error
        with pytest.raises(TTSError, match="Failed to generate audio"):
            provider.generate_audio(mock_client, speaker_config, "Test text")

    @patch.dict(os.environ, {"OPENAI_API_KEY": "fake_api_key"})
    def test_generate_audio_rate_limit_error(self):
        """Test generate_audio with rate limit error."""
        provider = OpenAITTSProvider()

        # Create mock client
        mock_client = MagicMock()

        # Create speaker config
        speaker_config = {"voice": "alloy"}

        # Create a proper exception structure for RateLimitError
        class MockRateLimitError(Exception):
            def __str__(self):
                return "Rate limit exceeded"

        # Make API call raise rate limit error
        mock_client.audio.speech.create.side_effect = MockRateLimitError()

        # Should raise TTSError for rate limit error
        with pytest.raises(TTSError, match="Failed to generate audio"):
            provider.generate_audio(mock_client, speaker_config, "Test text")

    @patch.dict(os.environ, {"OPENAI_API_KEY": "fake_api_key"})
    def test_generate_audio_api_error(self):
        """Test generate_audio with API error."""
        provider = OpenAITTSProvider()

        # Create mock client
        mock_client = MagicMock()

        # Create speaker config
        speaker_config = {"voice": "alloy"}

        # Create a proper exception structure for APIError
        class MockAPIError(Exception):
            def __str__(self):
                return "API error"

        # Make API call raise API error
        mock_client.audio.speech.create.side_effect = MockAPIError()

        # Should raise TTSError for API error
        with pytest.raises(TTSError, match="Failed to generate audio"):
            provider.generate_audio(mock_client, speaker_config, "Test text")

    @patch.dict(os.environ, {"OPENAI_API_KEY": "fake_api_key"})
    def test_generate_audio_generic_error(self):
        """Test generate_audio with generic error."""
        provider = OpenAITTSProvider()

        # Create mock client
        mock_client = MagicMock()

        # Create speaker config
        speaker_config = {"voice": "alloy"}

        # Make API call raise generic Exception
        mock_client.audio.speech.create.side_effect = Exception("Generic error")

        # Should raise TTSError for generic error
        with pytest.raises(TTSError, match="Failed to generate audio"):
            provider.generate_audio(mock_client, speaker_config, "Test text")

    # The _is_empty_value method has been removed in the refactoring
