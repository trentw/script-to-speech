import io
import json
import os
from unittest.mock import MagicMock, Mock, patch

import pytest
from zyphra import ZyphraError

from script_to_speech.tts_providers.base.exceptions import TTSError, VoiceNotFoundError
from script_to_speech.tts_providers.zonos.tts_provider import ZonosTTSProvider


class TestZonosTTSProvider:
    """Tests for the ZonosTTSProvider class."""

    def test_init(self):
        """Test initialization of the provider."""
        # No need to instantiate stateless providers
        # Just verify it's a subclass of StatelessTTSProviderBase
        from script_to_speech.tts_providers.base.stateless_tts_provider import (
            StatelessTTSProviderBase,
        )

        assert issubclass(ZonosTTSProvider, StatelessTTSProviderBase)

    def test_validate_config_valid(self):
        """Test validate_speaker_config with valid configuration."""
        # Test with minimal valid config (now a class method)
        valid_config = {"default_voice_name": "american_female"}
        ZonosTTSProvider.validate_speaker_config(valid_config)  # Should not raise

        # Test with all valid fields
        full_config = {
            "default_voice_name": "british_male",
            "speaking_rate": 20,
            "language_iso_code": "en-us",
        }
        ZonosTTSProvider.validate_speaker_config(full_config)  # Should not raise

    def test_validate_config_invalid_missing_default_voice_name(self):
        """Test validate_speaker_config with missing default_voice_name."""
        # Test with missing default_voice_name (now a class method)
        invalid_config = {"speaking_rate": 20}
        with pytest.raises(
            ValueError, match="Missing required field 'default_voice_name'"
        ):
            ZonosTTSProvider.validate_speaker_config(invalid_config)

    def test_validate_config_invalid_default_voice_name_type(self):
        """Test validate_speaker_config with invalid default_voice_name type."""
        # Test with non-string default_voice_name (now a class method)
        invalid_config = {"default_voice_name": 12345}
        with pytest.raises(
            ValueError, match="Field 'default_voice_name' must be a string"
        ):
            ZonosTTSProvider.validate_speaker_config(invalid_config)

    def test_validate_config_invalid_default_voice_name_value(self):
        """Test validate_speaker_config with invalid default_voice_name value."""
        # Test with invalid default_voice_name (now a class method)
        invalid_config = {"default_voice_name": "invalid_voice"}
        with pytest.raises(VoiceNotFoundError, match="Invalid default_voice_name"):
            ZonosTTSProvider.validate_speaker_config(invalid_config)

    def test_validate_config_invalid_speaking_rate_type(self):
        """Test validate_speaker_config with invalid speaking_rate type."""
        # Test with non-numeric speaking_rate (now a class method)
        invalid_config = {
            "default_voice_name": "american_female",
            "speaking_rate": "not_a_number",
        }
        with pytest.raises(ValueError, match="Field 'speaking_rate' must be a number"):
            ZonosTTSProvider.validate_speaker_config(invalid_config)

    def test_validate_config_invalid_speaking_rate_range(self):
        """Test validate_speaker_config with out-of-range speaking_rate."""
        # Test with speaking_rate too high (now a class method)
        invalid_config = {
            "default_voice_name": "american_female",
            "speaking_rate": ZonosTTSProvider.MAX_SPEAKING_RATE + 1,
        }
        with pytest.raises(ValueError, match="Invalid speaking_rate"):
            ZonosTTSProvider.validate_speaker_config(invalid_config)

        # Test with speaking_rate too low (now a class method)
        invalid_config = {
            "default_voice_name": "american_female",
            "speaking_rate": ZonosTTSProvider.MIN_SPEAKING_RATE - 1,
        }
        with pytest.raises(ValueError, match="Invalid speaking_rate"):
            ZonosTTSProvider.validate_speaker_config(invalid_config)

    def test_validate_config_invalid_language_type(self):
        """Test validate_speaker_config with invalid language_iso_code type."""
        # Test with non-string language_iso_code (now a class method)
        invalid_config = {
            "default_voice_name": "american_female",
            "language_iso_code": 123,
        }
        with pytest.raises(
            ValueError, match="Field 'language_iso_code' must be a string"
        ):
            ZonosTTSProvider.validate_speaker_config(invalid_config)

    def test_validate_config_invalid_language_value(self):
        """Test validate_speaker_config with invalid language_iso_code value."""
        # Test with invalid language_iso_code (now a class method)
        invalid_config = {
            "default_voice_name": "american_female",
            "language_iso_code": "invalid_language",
        }
        with pytest.raises(ValueError, match="Invalid language_iso_code"):
            ZonosTTSProvider.validate_speaker_config(invalid_config)

    def test_no_initialize_method(self):
        """Test that stateless providers don't have initialize method."""
        provider = ZonosTTSProvider()

        # Stateless providers should not have initialize method
        assert not hasattr(provider, "initialize")

    def test_instantiate_client(self):
        """Test instantiate_client class method."""
        with patch.dict(os.environ, {"ZONOS_API_KEY": "fake_api_key"}):
            with patch(
                "script_to_speech.tts_providers.zonos.tts_provider.ZyphraClient"
            ) as mock_zyphra_client:
                # Call the class method
                client = ZonosTTSProvider.instantiate_client()

                # Verify the client was created correctly
                mock_zyphra_client.assert_called_once_with(api_key="fake_api_key")
                assert client is not None

    def test_get_valid_voices(self):
        """Test get_valid_voices method."""
        # Get the valid voices
        valid_voices = ZonosTTSProvider.get_valid_voices()

        # Verify it's a set and contains expected voices
        assert isinstance(valid_voices, set)
        assert "american_female" in valid_voices
        assert "british_male" in valid_voices
        assert len(valid_voices) > 0

    def test_get_speaker_identifier(self):
        """Test get_speaker_identifier method."""
        provider = ZonosTTSProvider()

        # Test with direct config dictionaries instead of stored speaker configs
        # Minimal config
        default_id = provider.get_speaker_identifier(
            {"default_voice_name": "american_female"}
        )

        # Full config
        full_config = {
            "default_voice_name": "british_male",
            "speaking_rate": 20,
            "language_iso_code": "en-us",
        }
        bob_id = provider.get_speaker_identifier(full_config)

        # Verify identifiers format and uniqueness
        assert default_id.startswith("american_female_")
        assert bob_id.startswith("british_male_")
        assert default_id != bob_id  # Should be different due to different configs

    def test_get_speaker_identifier_invalid(self):
        """Test get_speaker_identifier with invalid config."""
        provider = ZonosTTSProvider()

        # Should raise for missing default_voice_name
        with pytest.raises(TTSError):
            provider.get_speaker_identifier({})

        # Should raise for invalid default_voice_name type
        with pytest.raises(TTSError):
            provider.get_speaker_identifier({"default_voice_name": None})

    # get_speaker_configuration method has been removed from provider and moved to TTSProviderManager

    def test_get_provider_identifier(self):
        """Test get_provider_identifier class method."""
        # Check provider identifier
        assert ZonosTTSProvider.get_provider_identifier() == "zonos"

    def test_get_yaml_instructions(self):
        """Test get_yaml_instructions class method."""
        # Check YAML instructions contain key information
        instructions = ZonosTTSProvider.get_yaml_instructions()
        assert "ZONOS_API_KEY" in instructions
        assert "default_voice_name:" in instructions
        assert "speaking_rate:" in instructions
        assert "language_iso_code:" in instructions

        # Check that it includes the valid voices
        valid_voices = ZonosTTSProvider.get_valid_voices()
        for voice in valid_voices:
            assert voice in instructions

    def test_get_required_fields(self):
        """Test get_required_fields class method."""
        # Check required fields
        required_fields = ZonosTTSProvider.get_required_fields()
        assert required_fields == ["default_voice_name"]

    def test_get_optional_fields(self):
        """Test get_optional_fields class method."""
        # Check optional fields
        optional_fields = ZonosTTSProvider.get_optional_fields()
        assert set(optional_fields) == {"speaking_rate", "language_iso_code"}

    def test_get_metadata_fields(self):
        """Test get_metadata_fields class method."""
        # Check metadata fields
        metadata_fields = ZonosTTSProvider.get_metadata_fields()
        assert isinstance(metadata_fields, list)

    def test_instantiate_client_missing_key(self, monkeypatch):
        """Test instantiate_client with missing API key."""
        # Ensure ZONOS_API_KEY is not set
        monkeypatch.delenv("ZONOS_API_KEY", raising=False)

        # Should raise for missing API key
        with pytest.raises(
            TTSError, match="ZONOS_API_KEY environment variable is not set"
        ):
            ZonosTTSProvider.instantiate_client()

    @patch.dict(os.environ, {"ZONOS_API_KEY": "fake_api_key"})
    @patch("script_to_speech.tts_providers.zonos.tts_provider.ZyphraClient")
    def test_instantiate_client_error(self, mock_zyphra_client):
        """Test instantiate_client with initialization error."""
        # Make ZyphraClient constructor raise exception
        mock_zyphra_client.side_effect = Exception("API initialization failed")

        # Should raise for initialization error
        with pytest.raises(TTSError, match="Failed to initialize Zyphra client"):
            ZonosTTSProvider.instantiate_client()

    @patch.dict(os.environ, {"ZONOS_API_KEY": "fake_api_key"})
    def test_generate_audio_success(self):
        """Test generate_audio method with successful generation."""
        provider = ZonosTTSProvider()

        # Create mock client
        mock_client = MagicMock()

        # Setup mock response
        mock_client.audio.speech.create.return_value = b"fake_audio_data"

        # Create basic speaker config
        speaker_config = {"default_voice_name": "american_female"}

        # Generate audio with passed client and config
        audio_data = provider.generate_audio(mock_client, speaker_config, "Test text")

        # Verify API was called correctly
        mock_client.audio.speech.create.assert_called_once_with(
            text="Test text",
            default_voice_name="american_female",
            mime_type=ZonosTTSProvider.MIME_TYPE,
        )
        assert audio_data == b"fake_audio_data"

    @patch.dict(os.environ, {"ZONOS_API_KEY": "fake_api_key"})
    def test_generate_audio_with_optional_params(self):
        """Test generate_audio method with optional parameters."""
        provider = ZonosTTSProvider()

        # Create mock client
        mock_client = MagicMock()

        # Setup mock response
        mock_client.audio.speech.create.return_value = b"fake_audio_data"

        # Create config with optional parameters
        speaker_config = {
            "default_voice_name": "british_male",
            "speaking_rate": 20,
            "language_iso_code": "en-us",
        }

        # Generate audio with optional parameters
        audio_data = provider.generate_audio(mock_client, speaker_config, "Test text")

        # Verify API was called with all parameters
        mock_client.audio.speech.create.assert_called_once_with(
            text="Test text",
            default_voice_name="british_male",
            mime_type=ZonosTTSProvider.MIME_TYPE,
            speaking_rate=20,
            language_iso_code="en-us",
        )
        assert audio_data == b"fake_audio_data"

    @patch.dict(os.environ, {"ZONOS_API_KEY": "fake_api_key"})
    def test_generate_audio_client_none(self):
        """Test generate_audio with None client."""
        provider = ZonosTTSProvider()

        # Generate audio with None client should raise error
        with pytest.raises(TTSError, match="Zyphra client is not initialized"):
            provider.generate_audio(
                None, {"default_voice_name": "american_female"}, "Test text"
            )

    @patch.dict(os.environ, {"ZONOS_API_KEY": "fake_api_key"})
    def test_generate_audio_zyphra_error(self):
        """Test generate_audio with Zyphra API error."""
        provider = ZonosTTSProvider()

        # Create mock client
        mock_client = MagicMock()

        # Create speaker config
        speaker_config = {"default_voice_name": "american_female"}

        # Create a proper exception structure for ZyphraError
        class MockZyphraError(Exception):
            def __str__(self):
                return "Zyphra API error"

        # Make API call raise Zyphra error
        mock_client.audio.speech.create.side_effect = MockZyphraError()

        # Should raise TTSError for Zyphra error
        with pytest.raises(TTSError, match="Zyphra API error"):
            provider.generate_audio(mock_client, speaker_config, "Test text")

    @patch.dict(os.environ, {"ZONOS_API_KEY": "fake_api_key"})
    def test_generate_audio_generic_error(self):
        """Test generate_audio with generic error."""
        provider = ZonosTTSProvider()

        # Create mock client
        mock_client = MagicMock()

        # Create speaker config
        speaker_config = {"default_voice_name": "american_female"}

        # Make API call raise generic Exception
        mock_client.audio.speech.create.side_effect = Exception("Generic error")

        # Should raise TTSError for generic error
        with pytest.raises(TTSError, match="Failed to generate audio"):
            provider.generate_audio(mock_client, speaker_config, "Test text")
