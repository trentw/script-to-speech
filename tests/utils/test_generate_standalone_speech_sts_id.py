"""Tests for generate_standalone_speech sts_id functionality."""

import argparse
import sys
from unittest.mock import MagicMock, patch

import pytest

from script_to_speech.utils.generate_standalone_speech import (
    _build_tts_config_data,
    main,
)


class TestBuildTtsConfigDataWithStsId:
    """Tests for _build_tts_config_data function with sts_id support."""

    def test_build_tts_config_data_with_sts_id(self):
        """Test _build_tts_config_data when sts_id is provided."""
        # Arrange
        mock_args = MagicMock()
        mock_args.sts_id = "test_voice_id"
        mock_args.provider = "test_provider"
        mock_args.custom_param = "custom_value"  # Optional override
        # Set other fields to None to simulate they weren't provided
        mock_args.voice = None
        mock_args.model = None
        mock_args.speed = None

        mock_provider_class = MagicMock()
        mock_provider_class.get_required_fields.return_value = ["voice", "model"]
        mock_provider_class.get_optional_fields.return_value = ["speed", "custom_param"]

        # Act
        result = _build_tts_config_data(mock_args, mock_provider_class)

        # Assert
        expected = {
            "default": {
                "provider": "test_provider",
                "sts_id": "test_voice_id",
                "custom_param": "custom_value",
            }
        }
        assert result == expected

    def test_build_tts_config_data_with_sts_id_no_overrides(self):
        """Test _build_tts_config_data with sts_id but no override parameters."""
        # Arrange
        mock_args = MagicMock()
        mock_args.sts_id = "test_voice_id"
        mock_args.provider = "test_provider"
        mock_args.voice = None  # No override
        mock_args.model = None  # No override
        mock_args.speed = None  # No override

        mock_provider_class = MagicMock()
        mock_provider_class.get_required_fields.return_value = ["voice", "model"]
        mock_provider_class.get_optional_fields.return_value = ["speed"]

        # Act
        result = _build_tts_config_data(mock_args, mock_provider_class)

        # Assert
        expected = {"default": {"provider": "test_provider", "sts_id": "test_voice_id"}}
        assert result == expected

    def test_build_tts_config_data_with_sts_id_skip_provider_field(self):
        """Test _build_tts_config_data with sts_id skips provider field in overrides."""
        # Arrange
        mock_args = MagicMock()
        mock_args.sts_id = "test_voice_id"
        mock_args.provider = "test_provider"
        mock_args.voice = "override_voice"

        mock_provider_class = MagicMock()
        mock_provider_class.get_required_fields.return_value = ["provider", "voice"]
        mock_provider_class.get_optional_fields.return_value = []

        # Act
        result = _build_tts_config_data(mock_args, mock_provider_class)

        # Assert
        expected = {
            "default": {
                "provider": "test_provider",
                "sts_id": "test_voice_id",
                "voice": "override_voice",
            }
        }
        assert result == expected
        # Provider should not be duplicated in the config

    def test_build_tts_config_data_without_sts_id_normal_flow(self):
        """Test _build_tts_config_data without sts_id follows normal validation flow."""
        # Arrange
        mock_args = MagicMock()
        mock_args.sts_id = None
        mock_args.provider = "test_provider"
        mock_args.voice = "test_voice"
        mock_args.model = "test_model"
        mock_args.speed = 1.0

        mock_provider_class = MagicMock()
        mock_provider_class.get_required_fields.return_value = ["voice", "model"]
        mock_provider_class.get_optional_fields.return_value = ["speed"]

        # Act
        result = _build_tts_config_data(mock_args, mock_provider_class)

        # Assert
        expected = {
            "default": {
                "provider": "test_provider",
                "voice": "test_voice",
                "model": "test_model",
                "speed": 1.0,
            }
        }
        assert result == expected

    def test_build_tts_config_data_without_sts_id_missing_required(self):
        """Test _build_tts_config_data without sts_id raises error for missing required fields."""
        # Arrange
        mock_args = MagicMock()
        mock_args.sts_id = None
        mock_args.provider = "test_provider"
        mock_args.voice = "test_voice"
        # Remove the model attribute to simulate missing argument
        del mock_args.model

        mock_provider_class = MagicMock()
        mock_provider_class.get_required_fields.return_value = ["voice", "model"]
        mock_provider_class.get_optional_fields.return_value = []

        # Act & Assert
        with pytest.raises(AttributeError):
            _build_tts_config_data(mock_args, mock_provider_class)


class TestMainWithStsId:
    """Tests for main function with sts_id support."""

    @patch("script_to_speech.utils.generate_standalone_speech.argparse.ArgumentParser")
    @patch("script_to_speech.utils.generate_standalone_speech.get_provider_class")
    @patch(
        "script_to_speech.utils.generate_standalone_speech.generate_standalone_speech"
    )
    @patch("script_to_speech.utils.generate_standalone_speech.TTSProviderManager")
    @patch("script_to_speech.utils.env_utils.load_environment_variables")
    def test_main_with_sts_id_present_in_argv(
        self,
        mock_load_env,
        mock_tts_manager_class,
        mock_generate,
        mock_get_provider,
        mock_parser_class,
    ):
        """Test main function when --sts_id is present in sys.argv."""
        # Arrange
        mock_load_env.return_value = True

        # Mock sys.argv to include --sts_id
        test_argv = ["script", "test_provider", "--sts_id", "test_voice", "Hello world"]

        mock_parser = MagicMock()
        mock_parser_class.return_value = mock_parser

        # Mock the temporary args parsing
        mock_temp_args = MagicMock()
        mock_temp_args.provider = "test_provider"
        mock_parser.parse_known_args.return_value = (mock_temp_args, [])

        # Mock the final args parsing
        mock_final_args = MagicMock()
        mock_final_args.provider = "test_provider"
        mock_final_args.sts_id = "test_voice"
        mock_final_args.text = ["Hello world"]
        mock_final_args.output_dir = "output"
        mock_final_args.split_audio = False
        mock_final_args.variant_num = 1
        mock_parser.parse_args.return_value = mock_final_args

        mock_provider_class = MagicMock()
        mock_provider_class.get_required_fields.return_value = ["voice"]
        mock_provider_class.get_optional_fields.return_value = []
        mock_get_provider.return_value = mock_provider_class

        mock_tts_manager = MagicMock()
        mock_tts_manager_class.return_value = mock_tts_manager

        # Act
        with patch("sys.argv", test_argv):
            result = main()

        # Assert
        assert result == 0

        # Verify that required fields are not marked as required when sts_id is present
        add_argument_calls = mock_parser.add_argument.call_args_list
        voice_arg_call = None
        for call in add_argument_calls:
            if call[0][0] == "--voice":
                voice_arg_call = call
                break

        assert voice_arg_call is not None
        assert (
            voice_arg_call[1]["required"] == False
        )  # Should be False when sts_id is present

    @patch("script_to_speech.utils.generate_standalone_speech.argparse.ArgumentParser")
    @patch("script_to_speech.utils.generate_standalone_speech.get_provider_class")
    @patch(
        "script_to_speech.utils.generate_standalone_speech.generate_standalone_speech"
    )
    @patch("script_to_speech.utils.generate_standalone_speech.TTSProviderManager")
    @patch("script_to_speech.utils.env_utils.load_environment_variables")
    def test_main_without_sts_id_in_argv(
        self,
        mock_load_env,
        mock_tts_manager_class,
        mock_generate,
        mock_get_provider,
        mock_parser_class,
    ):
        """Test main function when --sts_id is not present in sys.argv."""
        # Arrange
        mock_load_env.return_value = True

        # Mock sys.argv without --sts_id
        test_argv = ["script", "test_provider", "--voice", "test_voice", "Hello world"]

        mock_parser = MagicMock()
        mock_parser_class.return_value = mock_parser

        # Mock the temporary args parsing
        mock_temp_args = MagicMock()
        mock_temp_args.provider = "test_provider"
        mock_parser.parse_known_args.return_value = (mock_temp_args, [])

        # Mock the final args parsing
        mock_final_args = MagicMock()
        mock_final_args.provider = "test_provider"
        mock_final_args.sts_id = None
        mock_final_args.voice = "test_voice"
        mock_final_args.text = ["Hello world"]
        mock_final_args.output_dir = "output"
        mock_final_args.split_audio = False
        mock_final_args.variant_num = 1
        mock_parser.parse_args.return_value = mock_final_args

        mock_provider_class = MagicMock()
        mock_provider_class.get_required_fields.return_value = ["voice"]
        mock_provider_class.get_optional_fields.return_value = []
        mock_get_provider.return_value = mock_provider_class

        mock_tts_manager = MagicMock()
        mock_tts_manager_class.return_value = mock_tts_manager

        # Act
        with patch("sys.argv", test_argv):
            result = main()

        # Assert
        assert result == 0

        # Verify that required fields are marked as required when sts_id is not present
        add_argument_calls = mock_parser.add_argument.call_args_list
        voice_arg_call = None
        for call in add_argument_calls:
            if call[0][0] == "--voice":
                voice_arg_call = call
                break

        assert voice_arg_call is not None
        assert (
            voice_arg_call[1]["required"] == True
        )  # Should be True when sts_id is not present

    @patch("script_to_speech.utils.generate_standalone_speech.argparse.ArgumentParser")
    @patch("script_to_speech.utils.generate_standalone_speech.get_provider_class")
    def test_main_sts_id_help_text_modification(
        self, mock_get_provider, mock_parser_class
    ):
        """Test main function modifies help text when sts_id is present."""
        # Arrange
        test_argv = ["script", "test_provider", "--sts_id", "test_voice", "Hello world"]

        mock_parser = MagicMock()
        mock_parser_class.return_value = mock_parser

        # Mock the temporary args parsing
        mock_temp_args = MagicMock()
        mock_temp_args.provider = "test_provider"
        mock_parser.parse_known_args.return_value = (mock_temp_args, [])

        # Mock parse_args to raise SystemExit (like --help would)
        mock_parser.parse_args.side_effect = SystemExit(0)

        mock_provider_class = MagicMock()
        mock_provider_class.get_required_fields.return_value = ["voice", "model"]
        mock_provider_class.get_optional_fields.return_value = []
        mock_get_provider.return_value = mock_provider_class

        # Act & Assert
        with patch("sys.argv", test_argv):
            with pytest.raises(SystemExit):
                main()

        # Verify help text includes sts_id modification
        add_argument_calls = mock_parser.add_argument.call_args_list
        voice_arg_call = None
        for call in add_argument_calls:
            if call[0][0] == "--voice":
                voice_arg_call = call
                break

        assert voice_arg_call is not None
        help_text = voice_arg_call[1]["help"]
        assert "(ignored if --sts_id is provided)" in help_text

    def test_sts_id_detection_logic(self):
        """Test the sts_id detection logic in sys.argv."""
        # Test cases for sts_id detection
        test_cases = [
            (["script", "provider", "--sts_id", "voice"], True),
            (["script", "provider", "--sts_id=voice"], True),
            (["script", "provider", "--voice", "voice"], False),
            (["script", "provider", "--other-sts_id", "voice"], False),
            (["script", "provider", "text_with_sts_id"], False),
        ]

        for argv, expected in test_cases:
            # Simulate the detection logic from the main function
            sts_id_present = any(
                arg == "--sts_id" or arg.startswith("--sts_id=") for arg in argv
            )
            assert sts_id_present == expected, f"Failed for argv: {argv}"
