import json
import os
from unittest.mock import MagicMock, patch

import pytest
import requests

from script_to_speech.tts_providers.base.exceptions import TTSError, TTSRateLimitError
from script_to_speech.tts_providers.minimax.tts_provider import MinimaxTTSProvider


class TestMinimaxTTSProvider:
    """Tests for the MinimaxTTSProvider class."""

    def test_get_provider_identifier(self):
        """Test get_provider_identifier returns the correct identifier."""
        assert MinimaxTTSProvider.get_provider_identifier() == "minimax"

    def test_get_required_fields(self):
        """Test get_required_fields returns the correct fields."""
        assert MinimaxTTSProvider.get_required_fields() == ["voice_id"]

    def test_get_optional_fields(self):
        """Test get_optional_fields returns the correct fields."""
        expected_fields = {
            "voice_mix",
            "speed",
            "volume",
            "pitch",
            "emotion",
            "english_normalization",
            "language_boost",
        }
        assert set(MinimaxTTSProvider.get_optional_fields()) == expected_fields

    def test_instantiate_client(self):
        """Test instantiate_client returns None as expected."""
        client = MinimaxTTSProvider.instantiate_client()
        assert client is None

    def test_validate_speaker_config_valid(self):
        """Test validate_speaker_config with valid config."""
        # Override VALID_VOICE_IDS for testing
        with patch.object(MinimaxTTSProvider, "VALID_VOICE_IDS", {"Confident_Man"}):
            # Test with required fields only
            config = {"voice_id": "Confident_Man"}
            # Should not raise an exception
            MinimaxTTSProvider.validate_speaker_config(config)

            # Test with optional fields
            config = {
                "voice_id": "Confident_Man",
                "speed": 1.5,
                "volume": 5.0,
                "pitch": 2,
                "emotion": "happy",
                "english_normalization": True,
                "language_boost": "English",
            }

            # Patch the valid sets for testing
            with (
                patch.object(MinimaxTTSProvider, "VALID_EMOTIONS", {"happy"}),
                patch.object(MinimaxTTSProvider, "VALID_LANGUAGE_BOOSTS", {"English"}),
            ):
                # Should not raise an exception
                MinimaxTTSProvider.validate_speaker_config(config)

    def test_validate_speaker_config_with_voice_mix(self):
        """Test validate_speaker_config with voice_mix."""
        # Override VALID_VOICE_IDS for testing
        with patch.object(
            MinimaxTTSProvider, "VALID_VOICE_IDS", {"Confident_Man", "Cheerful_Woman"}
        ):
            # Config with voice_mix only (no voice_id)
            config = {
                "voice_mix": [
                    {"voice_id": "Confident_Man", "weight": 70},
                    {"voice_id": "Cheerful_Woman", "weight": 30},
                ]
            }
            # Should not raise an exception
            MinimaxTTSProvider.validate_speaker_config(config)

    def test_validate_speaker_config_invalid(self):
        """Test validate_speaker_config with invalid config."""
        # Missing both voice_id and voice_mix
        with pytest.raises(
            ValueError, match="Either 'voice_id' or 'voice_mix' must be provided"
        ):
            MinimaxTTSProvider.validate_speaker_config({})

        # Both voice_id and voice_mix provided
        with pytest.raises(
            ValueError, match="Cannot provide both 'voice_id' and 'voice_mix'"
        ):
            MinimaxTTSProvider.validate_speaker_config(
                {
                    "voice_id": "Confident_Man",
                    "voice_mix": [{"voice_id": "Confident_Man", "weight": 100}],
                }
            )

        # Invalid voice_id type
        with pytest.raises(ValueError, match="must be a string"):
            MinimaxTTSProvider.validate_speaker_config({"voice_id": 123})

        # Invalid voice_id value
        with pytest.raises(ValueError, match="Invalid voice_id"):
            MinimaxTTSProvider.validate_speaker_config({"voice_id": "invalid_voice"})

    def test_validate_speaker_config_invalid_voice_mix(self):
        """Test validate_speaker_config with invalid voice_mix."""
        # Override VALID_VOICE_IDS for testing
        with patch.object(MinimaxTTSProvider, "VALID_VOICE_IDS", {"Confident_Man"}):
            # voice_mix not a list
            with pytest.raises(ValueError, match="must be a list"):
                MinimaxTTSProvider.validate_speaker_config({"voice_mix": "not_a_list"})

            # voice_mix empty
            with pytest.raises(ValueError, match="must contain 1-4 items"):
                MinimaxTTSProvider.validate_speaker_config({"voice_mix": []})

            # voice_mix too many items
            with pytest.raises(ValueError, match="must contain 1-4 items"):
                MinimaxTTSProvider.validate_speaker_config(
                    {
                        "voice_mix": [
                            {"voice_id": "Confident_Man", "weight": 20}
                            for _ in range(5)
                        ]
                    }
                )

            # voice_mix item not a dict
            with pytest.raises(ValueError, match="must be a dictionary"):
                MinimaxTTSProvider.validate_speaker_config(
                    {"voice_mix": ["not_a_dict"]}
                )

            # voice_mix missing voice_id
            with pytest.raises(ValueError, match="Missing 'voice_id'"):
                MinimaxTTSProvider.validate_speaker_config(
                    {"voice_mix": [{"weight": 100}]}
                )

            # voice_mix missing weight
            with pytest.raises(ValueError, match="Missing 'weight'"):
                MinimaxTTSProvider.validate_speaker_config(
                    {"voice_mix": [{"voice_id": "Confident_Man"}]}
                )

            # voice_mix invalid voice_id type
            with pytest.raises(ValueError, match="must be a string"):
                MinimaxTTSProvider.validate_speaker_config(
                    {"voice_mix": [{"voice_id": 123, "weight": 100}]}
                )

            # voice_mix invalid voice_id value
            with pytest.raises(ValueError, match="Invalid voice_id"):
                MinimaxTTSProvider.validate_speaker_config(
                    {"voice_mix": [{"voice_id": "invalid_voice", "weight": 100}]}
                )

            # voice_mix invalid weight type
            with pytest.raises(ValueError, match="must be an integer"):
                MinimaxTTSProvider.validate_speaker_config(
                    {
                        "voice_mix": [
                            {"voice_id": "Confident_Man", "weight": "not_an_int"}
                        ]
                    }
                )

            # voice_mix invalid weight range (too low)
            with pytest.raises(ValueError, match="must be between 1 and 100"):
                MinimaxTTSProvider.validate_speaker_config(
                    {"voice_mix": [{"voice_id": "Confident_Man", "weight": 0}]}
                )

            # voice_mix invalid weight range (too high)
            with pytest.raises(ValueError, match="must be between 1 and 100"):
                MinimaxTTSProvider.validate_speaker_config(
                    {"voice_mix": [{"voice_id": "Confident_Man", "weight": 101}]}
                )

    def test_validate_speaker_config_invalid_optional_fields(self):
        """Test validate_speaker_config with invalid optional fields."""
        # Override VALID_VOICE_IDS for testing
        with patch.object(MinimaxTTSProvider, "VALID_VOICE_IDS", {"Confident_Man"}):
            # Invalid speed type
            with pytest.raises(ValueError, match="must be a number"):
                MinimaxTTSProvider.validate_speaker_config(
                    {"voice_id": "Confident_Man", "speed": "not_a_number"}
                )

            # Invalid speed range (too low)
            with pytest.raises(ValueError, match="Must be between 0.5 and 2.0"):
                MinimaxTTSProvider.validate_speaker_config(
                    {"voice_id": "Confident_Man", "speed": 0.4}
                )

            # Invalid speed range (too high)
            with pytest.raises(ValueError, match="Must be between 0.5 and 2.0"):
                MinimaxTTSProvider.validate_speaker_config(
                    {"voice_id": "Confident_Man", "speed": 2.1}
                )

            # Invalid volume type
            with pytest.raises(ValueError, match="must be a number"):
                MinimaxTTSProvider.validate_speaker_config(
                    {"voice_id": "Confident_Man", "volume": "not_a_number"}
                )

            # Invalid volume range (too low)
            with pytest.raises(ValueError, match="Must be between >0.0 and 10.0"):
                MinimaxTTSProvider.validate_speaker_config(
                    {"voice_id": "Confident_Man", "volume": 0.0}
                )

            # Invalid volume range (too high)
            with pytest.raises(ValueError, match="Must be between >0.0 and 10.0"):
                MinimaxTTSProvider.validate_speaker_config(
                    {"voice_id": "Confident_Man", "volume": 10.1}
                )

            # Invalid pitch type
            with pytest.raises(ValueError, match="must be an integer"):
                MinimaxTTSProvider.validate_speaker_config(
                    {"voice_id": "Confident_Man", "pitch": 1.5}
                )

            # Invalid pitch range (too low)
            with pytest.raises(ValueError, match="Must be between -12 and 12"):
                MinimaxTTSProvider.validate_speaker_config(
                    {"voice_id": "Confident_Man", "pitch": -13}
                )

            # Invalid pitch range (too high)
            with pytest.raises(ValueError, match="Must be between -12 and 12"):
                MinimaxTTSProvider.validate_speaker_config(
                    {"voice_id": "Confident_Man", "pitch": 13}
                )

            # Invalid emotion type
            with pytest.raises(ValueError, match="must be a string"):
                MinimaxTTSProvider.validate_speaker_config(
                    {"voice_id": "Confident_Man", "emotion": 123}
                )

            # Invalid emotion value
            with pytest.raises(ValueError, match="Invalid emotion"):
                MinimaxTTSProvider.validate_speaker_config(
                    {"voice_id": "Confident_Man", "emotion": "invalid_emotion"}
                )

            # Invalid english_normalization type
            with pytest.raises(ValueError, match="must be a boolean"):
                MinimaxTTSProvider.validate_speaker_config(
                    {"voice_id": "Confident_Man", "english_normalization": "not_a_bool"}
                )

            # Invalid language_boost type
            with pytest.raises(ValueError, match="must be a string"):
                MinimaxTTSProvider.validate_speaker_config(
                    {"voice_id": "Confident_Man", "language_boost": 123}
                )

            # Invalid language_boost value
            with pytest.raises(ValueError, match="Invalid language_boost"):
                MinimaxTTSProvider.validate_speaker_config(
                    {"voice_id": "Confident_Man", "language_boost": "invalid_language"}
                )

    def test_get_speaker_identifier(self):
        """Test get_speaker_identifier returns a consistent identifier."""
        # Override VALID_VOICE_IDS for testing
        with patch.object(MinimaxTTSProvider, "VALID_VOICE_IDS", {"Confident_Man"}):
            config = {"voice_id": "Confident_Man"}
            identifier = MinimaxTTSProvider.get_speaker_identifier(config)

            # Should be consistent for the same config
            assert MinimaxTTSProvider.get_speaker_identifier(config) == identifier

            # Should be different for different configs
            config2 = {"voice_id": "Confident_Man", "speed": 1.5}
            assert MinimaxTTSProvider.get_speaker_identifier(config2) != identifier

            # Should be different with voice_mix
            config3 = {"voice_mix": [{"voice_id": "Confident_Man", "weight": 100}]}
            assert MinimaxTTSProvider.get_speaker_identifier(config3) != identifier

    def test_get_speaker_identifier_missing_voice_definition(self):
        """Test get_speaker_identifier raises error when both voice_id and voice_mix are missing."""
        with pytest.raises(
            TTSError, match="Either 'voice_id' or 'voice_mix' must be provided"
        ):
            MinimaxTTSProvider.get_speaker_identifier({})

    @patch.dict(
        os.environ,
        {"MINIMAX_API_KEY": "fake-api-key", "MINIMAX_GROUP_ID": "fake-group-id"},
    )
    @patch("requests.post")
    def test_generate_audio_success(self, mock_post):
        """Test generate_audio successfully generates audio."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "base_resp": {"status_code": 0, "status_msg": "success"},
            "data": {"audio": "48656c6c6f20776f726c64"},  # "Hello world" in hex
        }
        mock_post.return_value = mock_response

        # Test config
        config = {"voice_id": "Confident_Man"}

        # Call generate_audio
        audio = MinimaxTTSProvider.generate_audio(None, config, "Hello world")

        # Verify the correct calls were made
        mock_post.assert_called_once()
        call_args, call_kwargs = mock_post.call_args

        # Check URL
        assert call_args[0].startswith(MinimaxTTSProvider.API_URL)
        assert "GroupId=fake-group-id" in call_args[0]

        # Check headers
        assert call_kwargs["headers"]["Authorization"] == "Bearer fake-api-key"
        assert call_kwargs["headers"]["Content-Type"] == "application/json"

        # Check payload
        payload = call_kwargs["json"]
        assert payload["model"] == MinimaxTTSProvider.MODEL_ID
        assert payload["text"] == "Hello world"
        assert payload["stream"] is False
        assert payload["voice_setting"]["voice_id"] == "Confident_Man"
        assert (
            payload["voice_setting"]["english_normalization"] is True
        )  # Default value
        assert payload["language_boost"] == "English"  # Default value
        assert (
            payload["audio_setting"]["sample_rate"]
            == MinimaxTTSProvider.AUDIO_SAMPLE_RATE
        )
        assert payload["audio_setting"]["bitrate"] == MinimaxTTSProvider.AUDIO_BITRATE
        assert payload["audio_setting"]["format"] == MinimaxTTSProvider.AUDIO_FORMAT
        assert payload["audio_setting"]["channel"] == MinimaxTTSProvider.AUDIO_CHANNELS
        assert payload["output_format"] == MinimaxTTSProvider.OUTPUT_FORMAT_API

        # Verify the result is the decoded hex
        assert audio == b"Hello world"

    @patch.dict(
        os.environ,
        {"MINIMAX_API_KEY": "fake-api-key", "MINIMAX_GROUP_ID": "fake-group-id"},
    )
    @patch("requests.post")
    def test_generate_audio_with_voice_mix(self, mock_post):
        """Test generate_audio with voice_mix."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "base_resp": {"status_code": 0, "status_msg": "success"},
            "data": {"audio": "48656c6c6f20776f726c64"},  # "Hello world" in hex
        }
        mock_post.return_value = mock_response

        # Test config with voice_mix only (no voice_id)
        config = {
            "voice_mix": [
                {"voice_id": "Confident_Man", "weight": 70},
                {"voice_id": "Cheerful_Woman", "weight": 30},
            ]
        }

        # Call generate_audio
        audio = MinimaxTTSProvider.generate_audio(None, config, "Hello world")

        # Verify voice_mix was used in the main payload
        payload = mock_post.call_args[1]["json"]
        assert "voice_setting" not in payload
        assert payload["timber_weights"] == config["voice_mix"]

    @patch.dict(
        os.environ,
        {"MINIMAX_API_KEY": "fake-api-key", "MINIMAX_GROUP_ID": "fake-group-id"},
    )
    @patch("requests.post")
    def test_generate_audio_with_default_values(self, mock_post):
        """Test generate_audio with default values for english_normalization and language_boost."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "base_resp": {"status_code": 0, "status_msg": "success"},
            "data": {"audio": "48656c6c6f20776f726c64"},  # "Hello world" in hex
        }
        mock_post.return_value = mock_response

        # Test config with minimal fields (no english_normalization or language_boost)
        config = {"voice_id": "Confident_Man"}

        # Call generate_audio
        audio = MinimaxTTSProvider.generate_audio(None, config, "Hello world")

        # Verify default values were used
        payload = mock_post.call_args[1]["json"]
        assert (
            payload["voice_setting"]["english_normalization"] is True
        )  # Default value
        assert payload["language_boost"] == "English"  # Default value

    @patch.dict(
        os.environ,
        {"MINIMAX_API_KEY": "fake-api-key", "MINIMAX_GROUP_ID": "fake-group-id"},
    )
    @patch("requests.post")
    def test_generate_audio_with_override_defaults(self, mock_post):
        """Test generate_audio with overridden default values."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "base_resp": {"status_code": 0, "status_msg": "success"},
            "data": {"audio": "48656c6c6f20776f726c64"},  # "Hello world" in hex
        }
        mock_post.return_value = mock_response

        # Test config with overridden defaults
        config = {
            "voice_id": "Confident_Man",
            "english_normalization": False,
            "language_boost": "Japanese",
        }

        # Call generate_audio
        audio = MinimaxTTSProvider.generate_audio(None, config, "Hello world")

        # Verify overridden values were used
        payload = mock_post.call_args[1]["json"]
        assert (
            payload["voice_setting"]["english_normalization"] is False
        )  # Overridden value
        assert payload["language_boost"] == "Japanese"  # Overridden value

    def test_validate_speaker_config_with_both_voice_id_and_voice_mix(self):
        """Test validate_speaker_config raises error when both voice_id and voice_mix are provided."""
        # Test config with both voice_id and voice_mix
        config = {
            "voice_id": "Confident_Man",
            "voice_mix": [{"voice_id": "Confident_Man", "weight": 100}],
        }

        # Call validate_speaker_config and expect ValueError
        with pytest.raises(
            ValueError, match="Cannot provide both 'voice_id' and 'voice_mix'"
        ):
            MinimaxTTSProvider.validate_speaker_config(config)

    @patch.dict(
        os.environ,
        {"MINIMAX_API_KEY": "fake-api-key", "MINIMAX_GROUP_ID": "fake-group-id"},
    )
    @patch("requests.post")
    def test_generate_audio_http_error(self, mock_post):
        """Test generate_audio handles HTTP errors."""
        # Setup mock response with error
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad request"
        mock_post.return_value = mock_response

        # Test config
        config = {"voice_id": "Confident_Man"}

        # Call generate_audio and expect TTSError
        with pytest.raises(TTSError, match="Minimax API HTTP error: 400"):
            MinimaxTTSProvider.generate_audio(None, config, "Hello world")

    @patch.dict(
        os.environ,
        {"MINIMAX_API_KEY": "fake-api-key", "MINIMAX_GROUP_ID": "fake-group-id"},
    )
    @patch("requests.post")
    def test_generate_audio_api_error(self, mock_post):
        """Test generate_audio handles API errors."""
        # Setup mock response with API error
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "base_resp": {"status_code": 400, "status_msg": "Invalid request"}
        }
        mock_post.return_value = mock_response

        # Test config
        config = {"voice_id": "Confident_Man"}

        # Call generate_audio and expect TTSError
        with pytest.raises(TTSError, match="Minimax API error: 400"):
            MinimaxTTSProvider.generate_audio(None, config, "Hello world")

    @patch.dict(
        os.environ,
        {"MINIMAX_API_KEY": "fake-api-key", "MINIMAX_GROUP_ID": "fake-group-id"},
    )
    @patch("requests.post")
    def test_generate_audio_rate_limit_error(self, mock_post):
        """Test generate_audio handles rate limit errors."""
        # Setup mock response with rate limit error
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "base_resp": {"status_code": 429, "status_msg": "Rate limit exceeded"}
        }
        mock_post.return_value = mock_response

        # Test config
        config = {"voice_id": "Confident_Man"}

        # Call generate_audio and expect TTSRateLimitError
        with pytest.raises(TTSRateLimitError, match="Minimax API rate limit exceeded"):
            MinimaxTTSProvider.generate_audio(None, config, "Hello world")

    @patch.dict(
        os.environ,
        {"MINIMAX_API_KEY": "fake-api-key", "MINIMAX_GROUP_ID": "fake-group-id"},
    )
    @patch("requests.post")
    def test_generate_audio_auth_failure_error(self, mock_post):
        """Test generate_audio handles authentication failure errors."""
        # Setup mock response with authentication failure error
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "base_resp": {"status_code": 1004, "status_msg": "Authentication failure"}
        }
        mock_post.return_value = mock_response

        # Test config
        config = {"voice_id": "Confident_Man"}

        # Call generate_audio and expect TTSError with specific message
        with pytest.raises(TTSError, match="Minimax API authentication failure"):
            MinimaxTTSProvider.generate_audio(None, config, "Hello world")

    @patch.dict(
        os.environ,
        {"MINIMAX_API_KEY": "fake-api-key", "MINIMAX_GROUP_ID": "fake-group-id"},
    )
    @patch("requests.post")
    def test_generate_audio_invalid_response(self, mock_post):
        """Test generate_audio handles invalid response format."""
        # Setup mock response with missing data
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "base_resp": {"status_code": 0, "status_msg": "success"},
            # Missing 'data' field
        }
        mock_post.return_value = mock_response

        # Test config
        config = {"voice_id": "Confident_Man"}

        # Call generate_audio and expect TTSError
        with pytest.raises(
            TTSError, match="Minimax API returned invalid response format"
        ):
            MinimaxTTSProvider.generate_audio(None, config, "Hello world")

    @patch("os.environ.get")
    def test_generate_audio_missing_api_key(self, mock_env_get):
        """Test generate_audio raises error when API key is missing."""
        # Configure the mock to return None for MINIMAX_API_KEY
        mock_env_get.side_effect = lambda key: (
            None if key == "MINIMAX_API_KEY" else "fake-group-id"
        )

        # Test config
        config = {"voice_id": "Confident_Man"}

        # Call generate_audio and expect TTSError
        with pytest.raises(
            TTSError, match="MINIMAX_API_KEY environment variable is not set"
        ):
            MinimaxTTSProvider.generate_audio(None, config, "Hello world")

    @patch("os.environ.get")
    def test_generate_audio_missing_group_id(self, mock_env_get):
        """Test generate_audio raises error when group ID is missing."""
        # Configure the mock to return None for MINIMAX_GROUP_ID
        mock_env_get.side_effect = lambda key: (
            "fake-api-key" if key == "MINIMAX_API_KEY" else None
        )

        # Test config
        config = {"voice_id": "Confident_Man"}

        # Call generate_audio and expect TTSError
        with pytest.raises(
            TTSError, match="MINIMAX_GROUP_ID environment variable is not set"
        ):
            MinimaxTTSProvider.generate_audio(None, config, "Hello world")

    @patch.dict(
        os.environ,
        {"MINIMAX_API_KEY": "fake-api-key", "MINIMAX_GROUP_ID": "fake-group-id"},
    )
    @patch("requests.post")
    def test_generate_audio_request_exception(self, mock_post):
        """Test generate_audio handles request exceptions."""
        # Setup mock to raise an exception
        mock_post.side_effect = requests.RequestException("Connection error")

        # Test config
        config = {"voice_id": "Confident_Man"}

        # Call generate_audio and expect TTSError
        with pytest.raises(TTSError, match="Request to Minimax API failed"):
            MinimaxTTSProvider.generate_audio(None, config, "Hello world")

    def test_get_max_download_threads(self):
        """Test get_max_download_threads returns the expected value."""
        assert MinimaxTTSProvider.get_max_download_threads() == 5
