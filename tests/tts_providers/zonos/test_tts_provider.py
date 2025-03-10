import io
import json
import os
from unittest.mock import MagicMock, Mock, patch

import pytest

from tts_providers.base.tts_provider import TTSError, VoiceNotFoundError
from tts_providers.zonos.tts_provider import ZonosTTSProvider


class TestZonosTTSProvider:
    """Tests for the ZonosTTSProvider class."""

    def test_init(self):
        """Test initialization of the provider."""
        provider = ZonosTTSProvider()
        assert provider.client is None
        assert provider.speaker_configs == {}

    def test_validate_config_valid(self):
        """Test validate_speaker_config with valid configuration."""
        provider = ZonosTTSProvider()

        # Test with minimal valid config
        valid_config = {"voice_seed": 12345}
        provider.validate_speaker_config(valid_config)  # Should not raise

        # Test with all valid fields
        full_config = {
            "voice_seed": 12345,
            "speaking_rate": 20,
            "language_iso_code": "en-us",
        }
        provider.validate_speaker_config(full_config)  # Should not raise

    def test_validate_config_invalid_missing_voice_seed(self):
        """Test validate_speaker_config with missing voice_seed."""
        provider = ZonosTTSProvider()

        # Test with missing voice_seed
        invalid_config = {"speaking_rate": 20}
        with pytest.raises(ValueError, match="Missing required field 'voice_seed'"):
            provider.validate_speaker_config(invalid_config)

    def test_validate_config_invalid_voice_seed_type(self):
        """Test validate_speaker_config with invalid voice_seed type."""
        provider = ZonosTTSProvider()

        # Test with non-integer voice_seed
        invalid_config = {"voice_seed": "not_an_int"}
        with pytest.raises(ValueError, match="invalid literal for int"):
            provider.validate_speaker_config(invalid_config)

    def test_validate_config_invalid_voice_seed_range(self):
        """Test validate_speaker_config with out-of-range voice_seed."""
        provider = ZonosTTSProvider()

        # Test with voice_seed too high
        invalid_config = {"voice_seed": ZonosTTSProvider.MAX_SEED + 1}
        with pytest.raises(ValueError, match="Invalid voice_seed"):
            provider.validate_speaker_config(invalid_config)

        # Test with voice_seed too low
        invalid_config = {"voice_seed": ZonosTTSProvider.MIN_SEED - 1}
        with pytest.raises(ValueError, match="Invalid voice_seed"):
            provider.validate_speaker_config(invalid_config)

    def test_validate_config_invalid_speaking_rate_type(self):
        """Test validate_speaker_config with invalid speaking_rate type."""
        provider = ZonosTTSProvider()

        # Test with non-numeric speaking_rate
        invalid_config = {"voice_seed": 12345, "speaking_rate": "not_a_number"}
        with pytest.raises(ValueError, match="Field 'speaking_rate' must be a number"):
            provider.validate_speaker_config(invalid_config)

    def test_validate_config_invalid_speaking_rate_range(self):
        """Test validate_speaker_config with out-of-range speaking_rate."""
        provider = ZonosTTSProvider()

        # Test with speaking_rate too high
        invalid_config = {
            "voice_seed": 12345,
            "speaking_rate": ZonosTTSProvider.MAX_SPEAKING_RATE + 1,
        }
        with pytest.raises(ValueError, match="Invalid speaking_rate"):
            provider.validate_speaker_config(invalid_config)

        # Test with speaking_rate too low
        invalid_config = {
            "voice_seed": 12345,
            "speaking_rate": ZonosTTSProvider.MIN_SPEAKING_RATE - 1,
        }
        with pytest.raises(ValueError, match="Invalid speaking_rate"):
            provider.validate_speaker_config(invalid_config)

    def test_validate_config_invalid_language_type(self):
        """Test validate_speaker_config with invalid language_iso_code type."""
        provider = ZonosTTSProvider()

        # Test with non-string language_iso_code
        invalid_config = {"voice_seed": 12345, "language_iso_code": 123}
        with pytest.raises(
            ValueError, match="Field 'language_iso_code' must be a string"
        ):
            provider.validate_speaker_config(invalid_config)

    def test_validate_config_invalid_language_value(self):
        """Test validate_speaker_config with invalid language_iso_code value."""
        provider = ZonosTTSProvider()

        # Test with invalid language_iso_code
        invalid_config = {"voice_seed": 12345, "language_iso_code": "invalid_language"}
        with pytest.raises(ValueError, match="Invalid language_iso_code"):
            provider.validate_speaker_config(invalid_config)

    def test_initialize(self):
        """Test initialize method with valid configurations."""
        provider = ZonosTTSProvider()

        # Create valid speaker configs
        speaker_configs = {
            "default": {"voice_seed": 12345},
            "BOB": {
                "voice_seed": 67890,
                "speaking_rate": 20,
                "language_iso_code": "en-us",
            },
            "ALICE": {"voice_seed": 54321, "speaking_rate": 15},
        }

        # Initialize the provider
        provider.initialize(speaker_configs)

        # Check that speaker configs were correctly stored
        assert len(provider.speaker_configs) == 3

        assert provider.speaker_configs["default"].voice_seed == 12345
        assert provider.speaker_configs["default"].speaking_rate is None
        assert provider.speaker_configs["default"].language_iso_code is None

        assert provider.speaker_configs["BOB"].voice_seed == 67890
        assert provider.speaker_configs["BOB"].speaking_rate == 20
        assert provider.speaker_configs["BOB"].language_iso_code == "en-us"

        assert provider.speaker_configs["ALICE"].voice_seed == 54321
        assert provider.speaker_configs["ALICE"].speaking_rate == 15
        assert provider.speaker_configs["ALICE"].language_iso_code is None

    def test_initialize_with_invalid_config(self):
        """Test initialize method with invalid configuration."""
        provider = ZonosTTSProvider()

        # Create invalid speaker configs
        speaker_configs = {
            "default": {"voice_seed": 12345},
            "INVALID": {"voice_seed": "not_an_int"},
        }

        # Initialize should raise for invalid voice_seed
        with pytest.raises(ValueError, match="invalid literal for int"):
            provider.initialize(speaker_configs)

    def test_get_speaker_identifier(self):
        """Test get_speaker_identifier method."""
        provider = ZonosTTSProvider()

        # Initialize with sample configs
        provider.initialize(
            {
                "default": {"voice_seed": 12345},
                "BOB": {
                    "voice_seed": 67890,
                    "speaking_rate": 20,
                    "language_iso_code": "en-us",
                },
            }
        )

        # Get identifiers for different speakers
        default_id = provider.get_speaker_identifier(None)
        bob_id = provider.get_speaker_identifier("BOB")

        # Verify identifiers format and uniqueness
        assert default_id.startswith("s12345_")
        assert bob_id.startswith("s67890_")
        assert default_id != bob_id  # Should be different due to different configs

    def test_get_speaker_identifier_not_found(self):
        """Test get_speaker_identifier with non-existent speaker."""
        provider = ZonosTTSProvider()

        # Initialize with only default
        provider.initialize({"default": {"voice_seed": 12345}})

        # Should raise for unknown speaker
        with pytest.raises(VoiceNotFoundError):
            provider.get_speaker_identifier("NON_EXISTENT")

    def test_get_speaker_configuration(self):
        """Test get_speaker_configuration method."""
        provider = ZonosTTSProvider()

        # Initialize with sample configs
        provider.initialize(
            {
                "default": {"voice_seed": 12345},
                "BOB": {
                    "voice_seed": 67890,
                    "speaking_rate": 20,
                    "language_iso_code": "en-us",
                },
                "ALICE": {"voice_seed": 54321, "speaking_rate": 15},
            }
        )

        # Check retrieved configs
        default_config = provider.get_speaker_configuration(None)
        assert default_config == {"voice_seed": 12345}

        bob_config = provider.get_speaker_configuration("BOB")
        assert bob_config == {
            "voice_seed": 67890,
            "speaking_rate": 20,
            "language_iso_code": "en-us",
        }

        alice_config = provider.get_speaker_configuration("ALICE")
        assert alice_config == {"voice_seed": 54321, "speaking_rate": 15}

    def test_get_speaker_configuration_not_found(self):
        """Test get_speaker_configuration with non-existent speaker."""
        provider = ZonosTTSProvider()

        # Initialize with only default
        provider.initialize({"default": {"voice_seed": 12345}})

        # Should raise for unknown speaker
        with pytest.raises(VoiceNotFoundError):
            provider.get_speaker_configuration("NON_EXISTENT")

    def test_get_provider_identifier(self):
        """Test get_provider_identifier class method."""
        # Check provider identifier
        assert ZonosTTSProvider.get_provider_identifier() == "zonos"

    def test_get_yaml_instructions(self):
        """Test get_yaml_instructions class method."""
        # Check YAML instructions contain key information
        instructions = ZonosTTSProvider.get_yaml_instructions()
        assert "ZONOS_API_KEY" in instructions
        assert "voice_seed:" in instructions
        assert "speaking_rate:" in instructions
        assert "language_iso_code:" in instructions

    def test_get_required_fields(self):
        """Test get_required_fields class method."""
        # Check required fields
        required_fields = ZonosTTSProvider.get_required_fields()
        assert required_fields == ["voice_seed"]

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

    @patch.dict(os.environ, {"ZONOS_API_KEY": "fake_api_key"})
    @patch("tts_providers.zonos.tts_provider.ZyphraClient")
    def test_initialize_api_client(self, mock_zyphra_client):
        """Test _initialize_api_client method."""
        provider = ZonosTTSProvider()

        # Call initialize_api_client
        provider._initialize_api_client()

        # Check API was initialized with key
        mock_zyphra_client.assert_called_once_with(api_key="fake_api_key")
        assert provider.client is not None

    def test_initialize_api_client_missing_key(self, monkeypatch):
        """Test _initialize_api_client with missing API key."""
        # Ensure ZONOS_API_KEY is not set
        monkeypatch.delenv("ZONOS_API_KEY", raising=False)

        provider = ZonosTTSProvider()

        # Should raise for missing API key
        with pytest.raises(
            TTSError, match="ZONOS_API_KEY environment variable is not set"
        ):
            provider._initialize_api_client()

    @patch.dict(os.environ, {"ZONOS_API_KEY": "fake_api_key"})
    @patch("tts_providers.zonos.tts_provider.ZyphraClient")
    def test_initialize_api_client_error(self, mock_zyphra_client):
        """Test _initialize_api_client with initialization error."""
        # Make ZyphraClient constructor raise exception
        mock_zyphra_client.side_effect = Exception("API initialization failed")

        provider = ZonosTTSProvider()

        # Should raise for initialization error
        with pytest.raises(TTSError, match="Failed to initialize Zyphra client"):
            provider._initialize_api_client()

    @patch.dict(os.environ, {"ZONOS_API_KEY": "fake_api_key"})
    def test_generate_audio_success(self):
        """Test generate_audio method with successful generation."""
        # Create provider with basic config
        provider = ZonosTTSProvider()
        provider.initialize({"default": {"voice_seed": 12345}})

        # Create mock client and replace the real one
        mock_client = MagicMock()
        provider.client = mock_client

        # Setup mock response
        mock_client.audio.speech.create.return_value = b"fake_audio_data"

        # Generate audio
        audio_data = provider.generate_audio(None, "Test text")

        # Verify API was called correctly
        mock_client.audio.speech.create.assert_called_once_with(
            text="Test text", seed=12345, mime_type=ZonosTTSProvider.MIME_TYPE
        )
        assert audio_data == b"fake_audio_data"

    @patch.dict(os.environ, {"ZONOS_API_KEY": "fake_api_key"})
    def test_generate_audio_with_speaker_and_options(self):
        """Test generate_audio method with specific speaker and optional parameters."""
        # Initialize provider with multiple speakers and optional parameters
        provider = ZonosTTSProvider()
        provider.initialize(
            {
                "default": {"voice_seed": 12345},
                "BOB": {
                    "voice_seed": 67890,
                    "speaking_rate": 20,
                    "language_iso_code": "en-us",
                },
            }
        )

        # Create mock client and replace the real one
        mock_client = MagicMock()
        provider.client = mock_client

        # Setup mock response
        mock_client.audio.speech.create.return_value = b"fake_audio_data"

        # Generate audio for specific speaker
        audio_data = provider.generate_audio("BOB", "Test text")

        # Verify API was called with all parameters
        mock_client.audio.speech.create.assert_called_once_with(
            text="Test text",
            seed=67890,
            mime_type=ZonosTTSProvider.MIME_TYPE,
            speaking_rate=20,
            language_iso_code="en-us",
        )
        assert audio_data == b"fake_audio_data"

    @patch.dict(os.environ, {"ZONOS_API_KEY": "fake_api_key"})
    def test_generate_audio_zyphra_error(self):
        """Test generate_audio with Zyphra API error."""
        # Initialize provider
        provider = ZonosTTSProvider()
        provider.initialize({"default": {"voice_seed": 12345}})

        # Create mock client and replace the real one
        mock_client = MagicMock()
        provider.client = mock_client

        # Create a proper exception structure
        class MockZyphraError(Exception):
            def __str__(self):
                return "Zyphra API error"

        # Make API call raise Zyphra error
        mock_client.audio.speech.create.side_effect = MockZyphraError()

        # Should raise TTSError for Zyphra error
        with pytest.raises(TTSError, match="Zyphra API error"):
            provider.generate_audio(None, "Test text")

    @patch.dict(os.environ, {"ZONOS_API_KEY": "fake_api_key"})
    def test_generate_audio_generic_error(self):
        """Test generate_audio with generic error."""
        # Initialize provider
        provider = ZonosTTSProvider()
        provider.initialize({"default": {"voice_seed": 12345}})

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
        provider = ZonosTTSProvider()

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
