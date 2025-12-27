"""
Tests for the dummy TTS provider override functionality.

This module tests the ability to override configured TTS providers with dummy TTS providers
for testing purposes.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import mock_open, patch

import pytest
import yaml

from script_to_speech.tts_providers.tts_provider_manager import TTSProviderManager


class TestDummyProviderOverride:
    """Tests for the dummy TTS provider override functionality."""

    @pytest.fixture
    def sample_config_file(self):
        """Create a temporary config file with non-dummy TTS providers."""
        config = {
            "default": {"provider": "openai", "model": "tts-1", "voice": "alloy"},
            "JOHN": {
                "provider": "elevenlabs",
                "voice_id": "some-voice-id",
                "model": "eleven_multilingual_v2",
            },
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as temp:
            yaml.dump(config, temp)
            temp_path = temp.name

        yield Path(temp_path)

        # Cleanup
        if os.path.exists(temp_path):
            os.remove(temp_path)

    def test_dummy_tts_provider_override_enabled(self, sample_config_file):
        """Test that providers are correctly overridden when dummy_tts_provider_override is True."""
        # Load the config file into a dictionary
        with open(sample_config_file, "r") as f:
            config_data_for_test = yaml.safe_load(f)

        # Initialize TTSProviderManager with dummy_tts_provider_override=True and config_data
        manager = TTSProviderManager(
            config_data=config_data_for_test, dummy_tts_provider_override=True
        )

        # Ensure the manager is initialized
        manager._ensure_initialized()

        # Check that the providers have been swapped to dummy TTS providers
        assert manager._speaker_providers["default"] == "dummy_stateless"
        assert manager._speaker_providers["JOHN"] == "dummy_stateful"

        # Check that dummy_id was added to the configs
        assert "dummy_id" in manager._speaker_configs_map["default"]
        assert manager._speaker_configs_map["default"]["dummy_id"] == "alloy"

        assert "dummy_id" in manager._speaker_configs_map["JOHN"]
        assert manager._speaker_configs_map["JOHN"]["dummy_id"] == "some-voice-id"

    def test_dummy_tts_provider_override_disabled(self, sample_config_file):
        """Test that providers are not overridden when dummy_tts_provider_override is False."""
        # Load the config file into a dictionary
        with open(sample_config_file, "r") as f:
            config_data_for_test = yaml.safe_load(f)

        # Initialize TTSProviderManager with dummy_tts_provider_override=False (default) and config_data
        manager = TTSProviderManager(
            config_data=config_data_for_test
        )  # dummy_tts_provider_override defaults to False

        # Ensure the manager is initialized
        manager._ensure_initialized()

        # Check that the providers have not been swapped
        assert manager._speaker_providers["default"] == "openai"
        assert manager._speaker_providers["JOHN"] == "elevenlabs"

        # Check that dummy_id was not added to the configs
        assert "dummy_id" not in manager._speaker_configs_map["default"]
        assert "dummy_id" not in manager._speaker_configs_map["JOHN"]

    def test_script_to_speech_integration(self, sample_config_file):
        """Test integration with script_to_speech.py."""
        import script_to_speech.script_to_speech as script_to_speech

        # Mock the parse_arguments function to return args with dummy_tts_provider_override=True
        # Also, prepare the expected config data that will be "loaded" by script_to_speech.main
        with open(sample_config_file, "r") as f:
            expected_config_data_for_assertion = yaml.safe_load(f)

        with (
            patch(
                "script_to_speech.script_to_speech.parse_arguments"
            ) as mock_parse_args,
            patch(
                "script_to_speech.script_to_speech.create_output_folders"
            ) as mock_create_folders,
            patch(
                "script_to_speech.script_to_speech.setup_screenplay_logging"
            ) as mock_setup_logging,
            patch(
                "script_to_speech.script_to_speech.configure_ffmpeg"
            ) as mock_configure_ffmpeg,
            patch(
                "os.path.exists", return_value=True
            ),  # Ensure main thinks the config file exists
            # Mock the file open and yaml.safe_load that script_to_speech.main will perform
            patch(
                "builtins.open",
                new_callable=mock_open,
                read_data=sample_config_file.read_text(),
            ) as mock_file_open_in_main,
            patch(
                "yaml.safe_load", return_value=expected_config_data_for_assertion
            ) as mock_yaml_load_in_main,
            patch(
                "script_to_speech.script_to_speech.TTSProviderManager"
            ) as mock_tts_manager,  # This is the one we assert against
            patch(
                "script_to_speech.script_to_speech.get_text_processor_configs"
            ) as mock_get_configs,
            patch(
                "script_to_speech.script_to_speech.TextProcessorManager"
            ) as mock_processor,
            patch(
                "script_to_speech.script_to_speech.load_json_chunks"
            ) as mock_load_chunks,
            patch(
                "script_to_speech.script_to_speech.plan_audio_generation"
            ) as mock_plan,
            patch(
                "script_to_speech.script_to_speech.print_unified_report"
            ) as mock_report,
            patch(
                "script_to_speech.script_to_speech.save_processed_dialogues"
            ) as mock_save_json,
            patch("os.makedirs") as mock_makedirs,  # From original test
            patch("sys.exit") as mock_exit,  # To prevent test from exiting
        ):

            # Configure parse_arguments mock
            args = type("Args", (), {})
            args.input_file = "input.json"
            args.gap = 500
            args.dry_run = True  # Use dry-run to simplify the test
            args.populate_cache = False
            args.check_silence = None
            args.cache_overrides = None
            args.optional_config = None
            args.tts_provider_config = sample_config_file
            args.provider = None
            args.text_processor_configs = None
            args.ffmpeg_path = None
            args.max_report_misses = 20
            args.max_report_text = 30
            args.dummy_tts_provider_override = True
            mock_parse_args.return_value = args

            # Configure folders mock
            mock_create_folders.return_value = (
                Path("output/folder"),
                Path("output/folder/cache"),
                Path("output/folder/logs"),
                Path("output/folder/logs/log.txt"),
            )

            # Configure load_chunks mock
            mock_load_chunks.return_value = [
                {"type": "dialogue", "text": "Hello", "speaker": "JOHN"},
            ]

            # Configure plan_audio_generation mock
            from unittest.mock import MagicMock

            from script_to_speech.audio_generation.models import (
                AudioGenerationTask,
                ReportingState,
            )

            mock_tasks = [
                MagicMock(
                    spec=AudioGenerationTask,
                    idx=0,
                    processed_dialogue={
                        "type": "dialogue",
                        "text": "Hello",
                        "speaker": "JOHN",
                    },
                )
            ]
            mock_plan.return_value = (mock_tasks, ReportingState())

            # Act
            script_to_speech.main()

            # Assert
            # Check that TTSProviderManager was initialized with the loaded config_data and dummy_tts_provider_override=True
            mock_tts_manager.assert_called_once_with(
                config_data=expected_config_data_for_assertion,
                overall_provider=None,  # As per args.provider being None in this test's setup for parse_args
                dummy_tts_provider_override=True,
            )

            # Ensure that script_to_speech.main attempted to load the correct config file
            mock_file_open_in_main.assert_called_once_with(
                sample_config_file, "r", encoding="utf-8"
            )
            mock_yaml_load_in_main.assert_called_once()

            # Check that create_output_folders was called with dummy_tts_provider_override=True
            mock_create_folders.assert_called_once_with(
                args.input_file, "dry-run", True  # dummy_tts_provider_override
            )
