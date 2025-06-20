import argparse
import os
import tempfile
from unittest.mock import MagicMock, Mock, mock_open, patch

import pytest
import yaml

from script_to_speech.utils.batch_standalone_speech_generator import (
    load_batch_config,
    main,
    process_configs,
    process_sts_ids,
)


class TestLoadBatchConfig:
    """Tests for the load_batch_config function."""

    def test_load_batch_config_valid_sts_ids(self):
        """Test loading a valid configuration with sts_ids."""
        config_data = {"text": "Hello world", "sts_ids": {"openai": ["alloy", "echo"]}}

        with patch("builtins.open", mock_open(read_data=yaml.dump(config_data))):
            with patch("yaml.safe_load", return_value=config_data):
                result = load_batch_config("test.yaml")

        assert result == config_data
        assert result["text"] == "Hello world"
        assert "openai" in result["sts_ids"]

    def test_load_batch_config_valid_configs(self):
        """Test loading a valid configuration with configs."""
        config_data = {
            "text": "Hello world",
            "configs": [
                {"provider": "openai", "voice": "alloy"},
                {"provider": "elevenlabs", "voice_id": "test"},
            ],
        }

        with patch("builtins.open", mock_open(read_data=yaml.dump(config_data))):
            with patch("yaml.safe_load", return_value=config_data):
                result = load_batch_config("test.yaml")

        assert result == config_data
        assert len(result["configs"]) == 2

    def test_load_batch_config_both_sts_ids_and_configs(self):
        """Test loading a configuration with both sts_ids and configs."""
        config_data = {
            "text": "Hello world",
            "sts_ids": {"openai": ["alloy"]},
            "configs": [{"provider": "elevenlabs", "voice_id": "test"}],
        }

        with patch("builtins.open", mock_open(read_data=yaml.dump(config_data))):
            with patch("yaml.safe_load", return_value=config_data):
                result = load_batch_config("test.yaml")

        assert result == config_data

    def test_load_batch_config_file_not_found(self):
        """Test loading from non-existent file."""
        with patch("builtins.open", side_effect=FileNotFoundError):
            with pytest.raises(ValueError, match="YAML file not found"):
                load_batch_config("nonexistent.yaml")

    def test_load_batch_config_invalid_yaml(self):
        """Test loading invalid YAML."""
        with patch("builtins.open", mock_open(read_data="invalid: yaml: content:")):
            with patch("yaml.safe_load", side_effect=yaml.YAMLError("Invalid YAML")):
                with pytest.raises(ValueError, match="Error parsing YAML file"):
                    load_batch_config("invalid.yaml")

    def test_load_batch_config_not_dict(self):
        """Test loading YAML that doesn't contain a dictionary."""
        with patch("builtins.open", mock_open(read_data="[]")):
            with patch("yaml.safe_load", return_value=[]):
                with pytest.raises(
                    ValueError, match="YAML file must contain a dictionary"
                ):
                    load_batch_config("list.yaml")

    def test_load_batch_config_missing_text(self):
        """Test loading configuration without text field."""
        config_data = {"sts_ids": {"openai": ["alloy"]}}

        with patch("builtins.open", mock_open(read_data=yaml.dump(config_data))):
            with patch("yaml.safe_load", return_value=config_data):
                with pytest.raises(
                    ValueError, match="YAML file must contain a 'text' field"
                ):
                    load_batch_config("no_text.yaml")

    def test_load_batch_config_text_not_string(self):
        """Test loading configuration with non-string text field."""
        config_data = {"text": 123, "sts_ids": {"openai": ["alloy"]}}

        with patch("builtins.open", mock_open(read_data=yaml.dump(config_data))):
            with patch("yaml.safe_load", return_value=config_data):
                with pytest.raises(ValueError, match="'text' field must be a string"):
                    load_batch_config("invalid_text.yaml")

    def test_load_batch_config_missing_both_fields(self):
        """Test loading configuration without sts_ids or configs."""
        config_data = {"text": "Hello world"}

        with patch("builtins.open", mock_open(read_data=yaml.dump(config_data))):
            with patch("yaml.safe_load", return_value=config_data):
                with pytest.raises(
                    ValueError,
                    match="YAML file must contain either 'sts_ids' or 'configs' field",
                ):
                    load_batch_config("no_config_fields.yaml")


class TestProcessStsIds:
    """Tests for the process_sts_ids function."""

    def create_mock_args(self, **kwargs):
        """Helper to create mock args object."""
        defaults = {
            "variants": 1,
            "output_dir": "test_output",
            "split_audio": False,
            "silence_threshold": -40,
            "min_silence_len": 500,
            "keep_silence": 100,
            "filename_addition": "",
        }
        defaults.update(kwargs)
        return argparse.Namespace(**defaults)

    @patch(
        "script_to_speech.utils.batch_standalone_speech_generator.generate_standalone_speech"
    )
    @patch(
        "script_to_speech.utils.batch_standalone_speech_generator.TTSProviderManager"
    )
    def test_process_sts_ids_single_provider(
        self, mock_tts_manager_class, mock_generate
    ):
        """Test processing sts_ids with single provider."""
        sts_ids_config = {"openai": ["alloy", "echo"]}
        text = "Hello world"
        args = self.create_mock_args()

        # Mock TTSProviderManager instance
        mock_tts_manager = MagicMock()
        mock_tts_manager_class.return_value = mock_tts_manager

        process_sts_ids(sts_ids_config, text, args)

        # Should create 2 TTSProviderManager instances (one for each sts_id)
        assert mock_tts_manager_class.call_count == 2

        # Should call generate_standalone_speech twice
        assert mock_generate.call_count == 2

        # Verify the generate_standalone_speech calls had correct parameters
        calls = mock_generate.call_args_list
        assert len(calls) == 2

        # Check first call (alloy)
        first_call = calls[0]
        assert first_call.kwargs["text"] == "Hello world"
        assert first_call.kwargs["variant_num"] == 1
        assert first_call.kwargs["output_dir"] == "test_output"
        assert first_call.kwargs["split_audio"] == False
        assert first_call.kwargs["silence_threshold"] == -40
        assert first_call.kwargs["min_silence_len"] == 500
        assert first_call.kwargs["keep_silence"] == 100
        assert first_call.kwargs["output_filename"] == "openai_alloy"

        # Check second call (echo)
        second_call = calls[1]
        assert second_call.kwargs["text"] == "Hello world"
        assert second_call.kwargs["output_filename"] == "openai_echo"

    @patch(
        "script_to_speech.utils.batch_standalone_speech_generator.generate_standalone_speech"
    )
    @patch(
        "script_to_speech.utils.batch_standalone_speech_generator.TTSProviderManager"
    )
    def test_process_sts_ids_multiple_providers(
        self, mock_tts_manager_class, mock_generate
    ):
        """Test processing sts_ids with multiple providers."""
        sts_ids_config = {"openai": ["alloy"], "elevenlabs": ["voice1", "voice2"]}
        text = "Hello world"
        args = self.create_mock_args()

        mock_tts_manager = MagicMock()
        mock_tts_manager_class.return_value = mock_tts_manager

        process_sts_ids(sts_ids_config, text, args)

        # Should create 3 TTSProviderManager instances total
        assert mock_tts_manager_class.call_count == 3
        assert mock_generate.call_count == 3

    @patch(
        "script_to_speech.utils.batch_standalone_speech_generator.generate_standalone_speech"
    )
    @patch(
        "script_to_speech.utils.batch_standalone_speech_generator.TTSProviderManager"
    )
    def test_process_sts_ids_with_variants(self, mock_tts_manager_class, mock_generate):
        """Test processing sts_ids with multiple variants."""
        sts_ids_config = {"openai": ["alloy"]}
        text = "Hello world"
        args = self.create_mock_args(variants=3)

        mock_tts_manager = MagicMock()
        mock_tts_manager_class.return_value = mock_tts_manager

        process_sts_ids(sts_ids_config, text, args)

        # Should call generate_standalone_speech 3 times (once per variant)
        assert mock_generate.call_count == 3

        # Check variant numbers
        variant_nums = [
            call.kwargs["variant_num"] for call in mock_generate.call_args_list
        ]
        assert variant_nums == [1, 2, 3]

    @patch(
        "script_to_speech.utils.batch_standalone_speech_generator.generate_standalone_speech"
    )
    @patch(
        "script_to_speech.utils.batch_standalone_speech_generator.TTSProviderManager"
    )
    def test_process_sts_ids_with_filename_addition(
        self, mock_tts_manager_class, mock_generate
    ):
        """Test processing sts_ids with filename addition."""
        sts_ids_config = {"openai": ["alloy"]}
        text = "Hello world"
        args = self.create_mock_args(filename_addition="test_suffix")

        mock_tts_manager = MagicMock()
        mock_tts_manager_class.return_value = mock_tts_manager

        process_sts_ids(sts_ids_config, text, args)

        # Verify output_filename includes the addition
        mock_generate.assert_called_once()
        assert (
            mock_generate.call_args.kwargs["output_filename"]
            == "openai_alloy_test_suffix"
        )

    @patch(
        "script_to_speech.utils.batch_standalone_speech_generator.generate_standalone_speech"
    )
    @patch(
        "script_to_speech.utils.batch_standalone_speech_generator.TTSProviderManager"
    )
    @patch("script_to_speech.utils.batch_standalone_speech_generator.logger")
    def test_process_sts_ids_with_error(
        self, mock_logger, mock_tts_manager_class, mock_generate
    ):
        """Test processing sts_ids when an error occurs."""
        sts_ids_config = {"openai": ["alloy", "echo"]}
        text = "Hello world"
        args = self.create_mock_args()

        # Mock first call to succeed, second to fail
        mock_tts_manager = MagicMock()
        mock_tts_manager_class.return_value = mock_tts_manager
        mock_generate.side_effect = [None, Exception("Generation error")]

        # Should not raise exception
        process_sts_ids(sts_ids_config, text, args)

        # Should log the error
        mock_logger.error.assert_called_once()
        assert "Generation error" in str(mock_logger.error.call_args)


class TestProcessConfigs:
    """Tests for the process_configs function."""

    def create_mock_args(self, **kwargs):
        """Helper to create mock args object."""
        defaults = {
            "variants": 1,
            "output_dir": "test_output",
            "split_audio": False,
            "silence_threshold": -40,
            "min_silence_len": 500,
            "keep_silence": 100,
        }
        defaults.update(kwargs)
        return argparse.Namespace(**defaults)

    @patch(
        "script_to_speech.utils.batch_standalone_speech_generator.generate_standalone_speech"
    )
    @patch(
        "script_to_speech.utils.batch_standalone_speech_generator.get_provider_class"
    )
    @patch(
        "script_to_speech.utils.batch_standalone_speech_generator.TTSProviderManager"
    )
    def test_process_configs_single_config(
        self, mock_tts_manager_class, mock_get_provider_class, mock_generate
    ):
        """Test processing configs with single configuration."""
        configs_list = [{"provider": "openai", "voice": "alloy"}]
        text = "Hello world"
        args = self.create_mock_args()

        # Mock provider class
        mock_provider_class = MagicMock()
        mock_get_provider_class.return_value = mock_provider_class

        # Mock TTSProviderManager instance
        mock_tts_manager = MagicMock()
        mock_tts_manager_class.return_value = mock_tts_manager

        process_configs(configs_list, text, args)

        # Should validate the config
        mock_provider_class.validate_speaker_config.assert_called_once()

        # Should create TTSProviderManager
        mock_tts_manager_class.assert_called_once()

        # Should call generate_standalone_speech
        mock_generate.assert_called_once()

    @patch(
        "script_to_speech.utils.batch_standalone_speech_generator.generate_standalone_speech"
    )
    @patch(
        "script_to_speech.utils.batch_standalone_speech_generator.get_provider_class"
    )
    @patch(
        "script_to_speech.utils.batch_standalone_speech_generator.TTSProviderManager"
    )
    def test_process_configs_multiple_configs(
        self, mock_tts_manager_class, mock_get_provider_class, mock_generate
    ):
        """Test processing configs with multiple configurations."""
        configs_list = [
            {"provider": "openai", "voice": "alloy"},
            {"provider": "elevenlabs", "voice_id": "test"},
        ]
        text = "Hello world"
        args = self.create_mock_args()

        mock_provider_class = MagicMock()
        mock_get_provider_class.return_value = mock_provider_class
        mock_tts_manager = MagicMock()
        mock_tts_manager_class.return_value = mock_tts_manager

        process_configs(configs_list, text, args)

        # Should process both configs
        assert mock_get_provider_class.call_count == 2
        assert mock_tts_manager_class.call_count == 2
        assert mock_generate.call_count == 2

    @patch(
        "script_to_speech.utils.batch_standalone_speech_generator.generate_standalone_speech"
    )
    @patch(
        "script_to_speech.utils.batch_standalone_speech_generator.get_provider_class"
    )
    @patch(
        "script_to_speech.utils.batch_standalone_speech_generator.TTSProviderManager"
    )
    @patch("script_to_speech.utils.batch_standalone_speech_generator.logger")
    def test_process_configs_invalid_config(
        self,
        mock_logger,
        mock_tts_manager_class,
        mock_get_provider_class,
        mock_generate,
    ):
        """Test processing configs with invalid configuration."""
        configs_list = [
            "not_a_dict",  # Invalid config
            {"provider": "openai", "voice": "alloy"},  # Valid config
        ]
        text = "Hello world"
        args = self.create_mock_args()

        mock_provider_class = MagicMock()
        mock_get_provider_class.return_value = mock_provider_class
        mock_tts_manager = MagicMock()
        mock_tts_manager_class.return_value = mock_tts_manager

        process_configs(configs_list, text, args)

        # Should log error for invalid config
        mock_logger.error.assert_called()
        assert "not a dictionary" in str(mock_logger.error.call_args_list[0])

        # Should still process the valid config
        assert mock_generate.call_count == 1

    @patch(
        "script_to_speech.utils.batch_standalone_speech_generator.generate_standalone_speech"
    )
    @patch(
        "script_to_speech.utils.batch_standalone_speech_generator.get_provider_class"
    )
    @patch(
        "script_to_speech.utils.batch_standalone_speech_generator.TTSProviderManager"
    )
    @patch("script_to_speech.utils.batch_standalone_speech_generator.logger")
    def test_process_configs_missing_provider(
        self,
        mock_logger,
        mock_tts_manager_class,
        mock_get_provider_class,
        mock_generate,
    ):
        """Test processing configs with missing provider field."""
        configs_list = [{"voice": "alloy"}]  # Missing provider
        text = "Hello world"
        args = self.create_mock_args()

        process_configs(configs_list, text, args)

        # Should log error for missing provider
        mock_logger.error.assert_called_once()
        assert "missing 'provider' field" in str(mock_logger.error.call_args)

        # Should not try to process the config
        mock_get_provider_class.assert_not_called()
        mock_generate.assert_not_called()

    @patch(
        "script_to_speech.utils.batch_standalone_speech_generator.generate_standalone_speech"
    )
    @patch(
        "script_to_speech.utils.batch_standalone_speech_generator.get_provider_class"
    )
    @patch(
        "script_to_speech.utils.batch_standalone_speech_generator.TTSProviderManager"
    )
    @patch("script_to_speech.utils.batch_standalone_speech_generator.logger")
    def test_process_configs_provider_error(
        self,
        mock_logger,
        mock_tts_manager_class,
        mock_get_provider_class,
        mock_generate,
    ):
        """Test processing configs when provider class raises error."""
        configs_list = [{"provider": "invalid_provider", "voice": "alloy"}]
        text = "Hello world"
        args = self.create_mock_args()

        # Mock get_provider_class to raise exception
        mock_get_provider_class.side_effect = Exception("Provider not found")

        process_configs(configs_list, text, args)

        # Should log the error
        mock_logger.error.assert_called_once()
        assert "Provider not found" in str(mock_logger.error.call_args)

        # Should not try to generate speech
        mock_generate.assert_not_called()


class TestMain:
    """Tests for the main function."""

    @patch("script_to_speech.utils.batch_standalone_speech_generator.process_sts_ids")
    @patch("script_to_speech.utils.batch_standalone_speech_generator.load_batch_config")
    @patch("script_to_speech.utils.batch_standalone_speech_generator.os.makedirs")
    @patch("sys.argv", ["script", "test.yaml"])
    def test_main_sts_ids_only(
        self, mock_makedirs, mock_load_config, mock_process_sts_ids
    ):
        """Test main function with sts_ids configuration only."""
        config_data = {"text": "Hello world", "sts_ids": {"openai": ["alloy", "echo"]}}
        mock_load_config.return_value = config_data

        result = main()

        assert result == 0
        mock_load_config.assert_called_once_with("test.yaml")
        mock_makedirs.assert_called_once_with("standalone_speech", exist_ok=True)
        mock_process_sts_ids.assert_called_once()

    @patch("script_to_speech.utils.batch_standalone_speech_generator.process_configs")
    @patch("script_to_speech.utils.batch_standalone_speech_generator.load_batch_config")
    @patch("script_to_speech.utils.batch_standalone_speech_generator.os.makedirs")
    @patch("sys.argv", ["script", "test.yaml"])
    def test_main_configs_only(
        self, mock_makedirs, mock_load_config, mock_process_configs
    ):
        """Test main function with configs configuration only."""
        config_data = {
            "text": "Hello world",
            "configs": [{"provider": "openai", "voice": "alloy"}],
        }
        mock_load_config.return_value = config_data

        result = main()

        assert result == 0
        mock_load_config.assert_called_once_with("test.yaml")
        mock_makedirs.assert_called_once_with("standalone_speech", exist_ok=True)
        mock_process_configs.assert_called_once()

    @patch("script_to_speech.utils.batch_standalone_speech_generator.process_sts_ids")
    @patch("script_to_speech.utils.batch_standalone_speech_generator.process_configs")
    @patch("script_to_speech.utils.batch_standalone_speech_generator.load_batch_config")
    @patch("script_to_speech.utils.batch_standalone_speech_generator.os.makedirs")
    @patch("sys.argv", ["script", "test.yaml"])
    def test_main_both_configurations(
        self,
        mock_makedirs,
        mock_load_config,
        mock_process_configs,
        mock_process_sts_ids,
    ):
        """Test main function with both sts_ids and configs."""
        config_data = {
            "text": "Hello world",
            "sts_ids": {"openai": ["alloy"]},
            "configs": [{"provider": "elevenlabs", "voice_id": "test"}],
        }
        mock_load_config.return_value = config_data

        result = main()

        assert result == 0
        mock_load_config.assert_called_once_with("test.yaml")
        mock_makedirs.assert_called_once_with("standalone_speech", exist_ok=True)
        mock_process_sts_ids.assert_called_once()
        mock_process_configs.assert_called_once()

    @patch("script_to_speech.utils.audio_utils.configure_ffmpeg")
    @patch("script_to_speech.utils.batch_standalone_speech_generator.process_sts_ids")
    @patch("script_to_speech.utils.batch_standalone_speech_generator.load_batch_config")
    @patch("script_to_speech.utils.batch_standalone_speech_generator.os.makedirs")
    @patch("sys.argv", ["script", "test.yaml", "--split-audio"])
    def test_main_with_split_audio(
        self,
        mock_makedirs,
        mock_load_config,
        mock_process_sts_ids,
        mock_configure_ffmpeg,
    ):
        """Test main function with split audio enabled."""
        config_data = {"text": "Hello world", "sts_ids": {"openai": ["alloy"]}}
        mock_load_config.return_value = config_data

        result = main()

        assert result == 0
        mock_configure_ffmpeg.assert_called_once()

    @patch("script_to_speech.utils.audio_utils.configure_ffmpeg")
    @patch("script_to_speech.utils.batch_standalone_speech_generator.load_batch_config")
    @patch("script_to_speech.utils.batch_standalone_speech_generator.logger")
    @patch("sys.argv", ["script", "test.yaml", "--split-audio"])
    def test_main_ffmpeg_error(
        self, mock_logger, mock_load_config, mock_configure_ffmpeg
    ):
        """Test main function when ffmpeg configuration fails."""
        config_data = {"text": "Hello world", "sts_ids": {"openai": ["alloy"]}}
        mock_load_config.return_value = config_data
        mock_configure_ffmpeg.side_effect = Exception("FFmpeg error")

        result = main()

        assert result == 1
        mock_logger.error.assert_called()
        assert "Error configuring ffmpeg" in str(mock_logger.error.call_args)

    @patch("script_to_speech.utils.batch_standalone_speech_generator.load_batch_config")
    @patch("script_to_speech.utils.batch_standalone_speech_generator.logger")
    @patch("sys.argv", ["script", "nonexistent.yaml"])
    def test_main_config_load_error(self, mock_logger, mock_load_config):
        """Test main function when config loading fails."""
        mock_load_config.side_effect = ValueError("Config error")

        result = main()

        assert result == 1
        mock_logger.error.assert_called()
        assert "Config error" in str(mock_logger.error.call_args)

    @patch("script_to_speech.utils.batch_standalone_speech_generator.load_batch_config")
    @patch("script_to_speech.utils.batch_standalone_speech_generator.os.makedirs")
    @patch(
        "sys.argv",
        ["script", "test.yaml", "--output-dir", "custom_output", "--variants", "3"],
    )
    def test_main_custom_args(self, mock_makedirs, mock_load_config):
        """Test main function with custom arguments."""
        config_data = {"text": "Hello world", "sts_ids": {"openai": ["alloy"]}}
        mock_load_config.return_value = config_data

        with patch(
            "script_to_speech.utils.batch_standalone_speech_generator.process_sts_ids"
        ) as mock_process:
            result = main()

            assert result == 0
            mock_makedirs.assert_called_once_with("custom_output", exist_ok=True)

            # Check that args were passed correctly
            call_args = mock_process.call_args
            assert call_args[0][2].output_dir == "custom_output"
            assert call_args[0][2].variants == 3
