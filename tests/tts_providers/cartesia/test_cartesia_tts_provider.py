import json
import os
from unittest.mock import MagicMock, patch

import pytest

from script_to_speech.tts_providers.base.exceptions import TTSError, TTSRateLimitError
from script_to_speech.tts_providers.cartesia.tts_provider import CartesiaTTSProvider


class TestCartesiaTTSProvider:
    """Tests for the CartesiaTTSProvider class."""

    def test_get_provider_identifier(self):
        """Test get_provider_identifier returns the correct identifier."""
        assert CartesiaTTSProvider.get_provider_identifier() == "cartesia"

    def test_get_required_fields(self):
        """Test get_required_fields returns the correct fields."""
        assert CartesiaTTSProvider.get_required_fields() == ["voice_id"]

    def test_get_optional_fields(self):
        """Test get_optional_fields returns the correct fields."""
        assert set(CartesiaTTSProvider.get_optional_fields()) == {"language", "speed"}

    def test_validate_speaker_config_valid(self):
        """Test validate_speaker_config with valid config."""
        config = {"voice_id": "test-voice-id"}
        # Should not raise an exception
        CartesiaTTSProvider.validate_speaker_config(config)

        # Test with optional fields
        config = {
            "voice_id": "test-voice-id",
            "language": "en",
            "speed": "normal",
        }
        # Should not raise an exception
        CartesiaTTSProvider.validate_speaker_config(config)

    def test_validate_speaker_config_invalid(self):
        """Test validate_speaker_config with invalid config."""
        # Missing required field
        with pytest.raises(ValueError, match="Missing required field 'voice_id'"):
            CartesiaTTSProvider.validate_speaker_config({})

        # Invalid voice_id type
        with pytest.raises(ValueError, match="must be a string"):
            CartesiaTTSProvider.validate_speaker_config({"voice_id": 123})

        # Invalid language
        with pytest.raises(ValueError, match="Invalid language"):
            CartesiaTTSProvider.validate_speaker_config(
                {"voice_id": "test-voice-id", "language": "invalid"}
            )

        # Invalid speed
        with pytest.raises(ValueError, match="Invalid speed"):
            CartesiaTTSProvider.validate_speaker_config(
                {"voice_id": "test-voice-id", "speed": "invalid"}
            )

    def test_get_speaker_identifier(self):
        """Test get_speaker_identifier returns a consistent identifier."""
        config = {"voice_id": "test-voice-id"}
        identifier = CartesiaTTSProvider.get_speaker_identifier(config)

        # Should be consistent for the same config
        assert CartesiaTTSProvider.get_speaker_identifier(config) == identifier

        # Should be different for different configs
        config2 = {"voice_id": "test-voice-id", "language": "fr"}
        assert CartesiaTTSProvider.get_speaker_identifier(config2) != identifier

    @patch.dict(os.environ, {"CARTESIA_API_KEY": "fake-api-key"})
    @patch("script_to_speech.tts_providers.cartesia.tts_provider.Cartesia")
    def test_instantiate_client(self, mock_cartesia):
        """Test instantiate_client creates a client with the API key."""
        mock_cartesia.return_value = MagicMock()

        client = CartesiaTTSProvider.instantiate_client()

        mock_cartesia.assert_called_once_with(api_key="fake-api-key")
        assert client == mock_cartesia.return_value

    @patch("script_to_speech.tts_providers.cartesia.tts_provider.os.environ.get")
    def test_instantiate_client_missing_api_key(self, mock_env_get):
        """Test instantiate_client raises an error when API key is missing."""
        # Configure the mock to return None for CARTESIA_API_KEY
        mock_env_get.return_value = None

        with pytest.raises(
            TTSError, match="CARTESIA_API_KEY environment variable is not set"
        ):
            CartesiaTTSProvider.instantiate_client()

    @patch("script_to_speech.tts_providers.cartesia.tts_provider.Cartesia")
    def test_generate_audio_success(self, mock_cartesia):
        """Test generate_audio successfully generates audio."""
        # Setup mock client
        mock_client = MagicMock()
        # Mock an iterator that returns chunks of bytes
        mock_client.tts.bytes.return_value = iter([b"chunk1", b"chunk2", b"chunk3"])

        # Test config
        config = {"voice_id": "test-voice-id"}

        # Call generate_audio
        audio = CartesiaTTSProvider.generate_audio(mock_client, config, "Hello world")

        # Verify the correct calls were made
        mock_client.tts.bytes.assert_called_once()
        call_kwargs = mock_client.tts.bytes.call_args.kwargs
        assert call_kwargs["model_id"] == "sonic-2"
        assert call_kwargs["transcript"] == "Hello world"
        assert call_kwargs["voice"]["mode"] == "id"
        assert call_kwargs["voice"]["id"] == "test-voice-id"
        assert call_kwargs["language"] == "en"
        assert call_kwargs["output_format"]["container"] == "mp3"

        # Verify the result is the concatenated chunks
        assert audio == b"chunk1chunk2chunk3"

    @patch("script_to_speech.tts_providers.cartesia.tts_provider.Cartesia")
    def test_generate_audio_with_options(self, mock_cartesia):
        """Test generate_audio with optional parameters."""
        # Setup mock client
        mock_client = MagicMock()
        # Mock an iterator that returns chunks of bytes
        mock_client.tts.bytes.return_value = iter([b"chunk1-fr", b"chunk2-fr"])

        # Test config with optional fields
        config = {
            "voice_id": "test-voice-id",
            "language": "fr",
            "speed": "fast",
        }

        # Call generate_audio
        audio = CartesiaTTSProvider.generate_audio(mock_client, config, "Bonjour")

        # Verify the correct calls were made
        call_kwargs = mock_client.tts.bytes.call_args.kwargs
        assert call_kwargs["language"] == "fr"
        assert call_kwargs["voice"]["experimental_controls"]["speed"] == "fast"

        # Verify the result is the concatenated chunks
        assert audio == b"chunk1-frchunk2-fr"

    @patch("script_to_speech.tts_providers.cartesia.tts_provider.Cartesia")
    def test_generate_audio_api_error(self, mock_cartesia):
        """Test generate_audio handles API errors."""
        # Setup mock client
        mock_client = MagicMock()

        # Create a mock ApiError
        from cartesia.core.api_error import ApiError

        api_error = ApiError(status_code=400, body={"error": "Bad request"})
        mock_client.tts.bytes.side_effect = api_error

        # Test config
        config = {"voice_id": "test-voice-id"}

        # Call generate_audio and expect TTSError
        with pytest.raises(TTSError, match="Cartesia API error"):
            CartesiaTTSProvider.generate_audio(mock_client, config, "Hello world")

    @patch("script_to_speech.tts_providers.cartesia.tts_provider.Cartesia")
    def test_generate_audio_rate_limit_error(self, mock_cartesia):
        """Test generate_audio handles rate limit errors."""
        # Setup mock client
        mock_client = MagicMock()

        # Create a mock ApiError with 429 status code
        from cartesia.core.api_error import ApiError

        api_error = ApiError(status_code=429, body={"error": "Too many requests"})
        mock_client.tts.bytes.side_effect = api_error

        # Test config
        config = {"voice_id": "test-voice-id"}

        # Call generate_audio and expect TTSRateLimitError
        with pytest.raises(TTSRateLimitError, match="Cartesia API rate limit exceeded"):
            CartesiaTTSProvider.generate_audio(mock_client, config, "Hello world")
