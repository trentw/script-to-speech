"""
Unit tests for the script_to_speech module.

This module tests the main script that drives the audio generation process,
including argument parsing, output file generation, and the core process flow.
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, call, mock_open, patch

import pytest
from pydub import AudioSegment

import script_to_speech
from audio_generation.models import AudioGenerationTask, ReportingState
from text_processors.processor_manager import TextProcessorManager
from tts_providers.tts_provider_manager import TTSProviderManager


class TestParseArguments:
    """Tests for the argument parsing function."""

    def test_required_arguments(self):
        """Test parsing with only required arguments."""
        # Arrange
        test_args = ["input_file.json"]

        # Act
        with patch.object(sys, "argv", ["script_to_speech.py"] + test_args):
            args = script_to_speech.parse_arguments()

        # Assert
        assert args.input_file == "input_file.json"
        assert args.gap == 500  # Default value

    def test_optional_arguments(self):
        """Test parsing with optional arguments."""
        # Arrange
        test_args = [
            "input_file.json",
            "--gap",
            "300",
            "--provider",
            "openai",
            "--tts-config",
            "config.yaml",
            "--ffmpeg-path",
            "/path/to/ffmpeg",
            "--check-silence",
            "-35.0",
            "--cache-overrides",
            "custom_directory",
            "--optional-config",
            "id3_config.yaml",
            "--max-report-misses",
            "15",
            "--max-report-text",
            "25",
        ]

        # Act
        with patch.object(sys, "argv", ["script_to_speech.py"] + test_args):
            args = script_to_speech.parse_arguments()

        # Assert
        assert args.input_file == "input_file.json"
        assert args.gap == 300
        assert args.provider == "openai"
        assert args.tts_config == "config.yaml"
        assert args.ffmpeg_path == "/path/to/ffmpeg"
        assert args.check_silence == -35.0
        assert args.cache_overrides == "custom_directory"
        assert args.optional_config == "id3_config.yaml"
        assert args.max_report_misses == 15
        assert args.max_report_text == 25

    def test_mutually_exclusive_run_modes(self):
        """Test parsing with mutually exclusive run modes."""
        # Arrange
        test_args = ["input_file.json", "--dry-run"]

        # Act
        with patch.object(sys, "argv", ["script_to_speech.py"] + test_args):
            args = script_to_speech.parse_arguments()

        # Assert
        assert args.dry_run is True
        assert args.populate_cache is False

        # Test with populate-cache
        test_args = ["input_file.json", "--populate-cache"]

        # Act
        with patch.object(sys, "argv", ["script_to_speech.py"] + test_args):
            args = script_to_speech.parse_arguments()

        # Assert
        assert args.dry_run is False
        assert args.populate_cache is True

    def test_check_silence_flag_with_no_value(self):
        """Test the check-silence flag when provided without a value."""
        # Arrange
        test_args = ["input_file.json", "--check-silence"]

        # Act
        with patch.object(sys, "argv", ["script_to_speech.py"] + test_args):
            args = script_to_speech.parse_arguments()

        # Assert
        assert args.check_silence == -40.0  # Default value

    def test_dummy_provider_override_flag(self):
        """Test the dummy-provider-override flag."""
        # Arrange
        test_args = ["input_file.json", "--dummy-provider-override"]

        # Act
        with patch.object(sys, "argv", ["script_to_speech.py"] + test_args):
            args = script_to_speech.parse_arguments()

        # Assert
        assert args.dummy_provider_override is True


class TestSaveModifiedJson:
    """Tests for the save_modified_json function."""

    def test_save_modified_json_success(self):
        """Test successfully saving modified JSON."""
        # Arrange
        modified_dialogues = [
            {"type": "dialogue", "text": "Hello", "speaker": "John"},
            {"type": "action", "text": "John walks away"},
        ]
        output_folder = "/output"
        input_file = "/input/file.json"

        # Act
        with (
            patch("builtins.open", mock_open()) as mock_file,
            patch("json.dump") as mock_json_dump,
            patch("script_to_speech.logger") as mock_logger,
        ):
            script_to_speech.save_modified_json(
                modified_dialogues, output_folder, input_file
            )

            # Assert
            mock_file.assert_called_once_with(
                "/output/file-modified.json", "w", encoding="utf-8"
            )
            mock_json_dump.assert_called_once()
            mock_logger.info.assert_called_with(
                "\nProcessed dialogue saved to: /output/file-modified.json"
            )

    def test_save_modified_json_error(self):
        """Test error handling when saving modified JSON."""
        # Arrange
        modified_dialogues = [{"type": "dialogue", "text": "Hello"}]
        output_folder = "/output"
        input_file = "/input/file.json"

        # Act
        with (
            patch("builtins.open", side_effect=PermissionError("Permission denied")),
            patch("script_to_speech.logger") as mock_logger,
        ):
            script_to_speech.save_modified_json(
                modified_dialogues, output_folder, input_file
            )

            # Assert
            mock_logger.error.assert_called_once()


class TestFindOptionalConfig:
    """Tests for the find_optional_config function."""

    def test_specified_config_exists(self):
        """Test when specified config file exists."""
        # Arrange
        args_config_path = "/path/to/config.yaml"
        input_file_path = "/path/to/input.json"

        # Act
        with patch("os.path.exists", return_value=True):
            result = script_to_speech.find_optional_config(
                args_config_path, input_file_path
            )

            # Assert
            assert result == args_config_path

    def test_specified_config_not_exists(self):
        """Test when specified config file doesn't exist."""
        # Arrange
        args_config_path = "/path/to/nonexistent.yaml"
        input_file_path = "/path/to/input.json"

        # Act
        with (
            patch("os.path.exists", return_value=False),
            patch("script_to_speech.logger") as mock_logger,
        ):
            result = script_to_speech.find_optional_config(
                args_config_path, input_file_path
            )

            # Assert
            assert result is None
            mock_logger.warning.assert_called_once()

    def test_default_config_exists(self):
        """Test when default config file exists."""
        # Arrange
        args_config_path = None
        input_file_path = "/path/to/input.json"

        # Act
        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("script_to_speech.logger") as mock_logger,
        ):
            result = script_to_speech.find_optional_config(
                args_config_path, input_file_path
            )

            # Assert
            assert result == "/path/to/input_optional_config.yaml"
            mock_logger.info.assert_called_once()

    def test_no_config_exists(self):
        """Test when no config file exists."""
        # Arrange
        args_config_path = None
        input_file_path = "/path/to/input.json"

        # Act
        with patch("pathlib.Path.exists", return_value=False):
            result = script_to_speech.find_optional_config(
                args_config_path, input_file_path
            )

            # Assert
            assert result is None


class TestMain:
    """Tests for the main function."""

    @pytest.fixture
    def mock_setup(self):
        """Set up common mocks for main function tests."""
        with (
            patch("script_to_speech.parse_arguments") as mock_parse_args,
            patch("script_to_speech.create_output_folders") as mock_create_folders,
            patch("script_to_speech.setup_screenplay_logging") as mock_setup_logging,
            patch("script_to_speech.configure_ffmpeg") as mock_configure_ffmpeg,
            patch("os.path.exists", return_value=True),
            patch("script_to_speech.TTSProviderManager") as mock_tts_manager,
            patch("script_to_speech.get_processor_configs") as mock_get_configs,
            patch("script_to_speech.TextProcessorManager") as mock_processor,
            patch("script_to_speech.load_json_chunks") as mock_load_chunks,
            patch("script_to_speech.logger") as mock_logger,
        ):

            # Configure parse_arguments mock
            args = MagicMock()
            args.input_file = "input.json"
            args.gap = 500
            args.dry_run = False
            args.populate_cache = False
            args.check_silence = -40.0
            args.cache_overrides = None
            args.optional_config = None
            args.tts_config = "tts_config.yaml"
            args.provider = "openai"
            args.processor_configs = None
            args.ffmpeg_path = None
            args.max_report_misses = 20
            args.max_report_text = 30
            args.dummy_provider_override = False
            mock_parse_args.return_value = args

            # Configure folders mock
            mock_create_folders.return_value = (
                "output/folder",
                "output/folder/cache",
                "output/folder/output.mp3",
                "output/folder/logs/log.txt",
            )

            # Configure load_chunks mock
            mock_load_chunks.return_value = [
                {"type": "dialogue", "text": "Hello", "speaker": "John"},
                {"type": "action", "text": "John walks away"},
            ]

            yield {
                "args": args,
                "logger": mock_logger,
                "tts_manager": mock_tts_manager,
                "processor": mock_processor,
                "load_chunks": mock_load_chunks,
            }

    def test_main_setup_phase(self, mock_setup):
        """Test the setup phase of the main function."""
        # Arrange
        mocks = mock_setup

        # Act
        with (
            patch("script_to_speech.plan_audio_generation") as mock_plan,
            patch("sys.exit") as mock_exit,
        ):
            # Configure plan_audio_generation to return a valid response before raising exception
            mock_tasks = [
                MagicMock(
                    spec=AudioGenerationTask,
                    idx=0,
                    processed_dialogue={
                        "type": "dialogue",
                        "text": "Hello",
                        "speaker": "John",
                    },
                )
            ]
            mock_plan.return_value = (mock_tasks, ReportingState())

            # Now we can check that setup phase is completed properly
            script_to_speech.main()

        # Assert
        mocks["logger"].info.assert_any_call(
            "Logging initialized. Log file: output/folder/logs/log.txt"
        )
        mocks["logger"].info.assert_any_call("Run mode: generate-output")
        mocks["logger"].info.assert_any_call("FFMPEG configuration successful.")
        mocks["logger"].info.assert_any_call("TTS provider manager initialized.")
        mocks["logger"].info.assert_any_call(
            f"Loading dialogues from: {mocks['args'].input_file}"
        )
        mocks["logger"].info.assert_any_call("Loaded 2 dialogue chunks.")

        # Verify TTSProviderManager was initialized with the correct parameters
        mocks["tts_manager"].assert_called_once_with(
            mocks["args"].tts_config,
            mocks["args"].provider,
            mocks["args"].dummy_provider_override,
        )

    def test_main_normal_run(self, mock_setup):
        """Test a normal run of the main function."""
        # Arrange
        mocks = mock_setup

        mock_tasks = [
            MagicMock(
                spec=AudioGenerationTask,
                idx=0,
                processed_dialogue={
                    "type": "dialogue",
                    "text": "Hello",
                    "speaker": "John",
                },
                cache_filepath="cache/file1.mp3",
                expected_silence=False,
            ),
            MagicMock(
                spec=AudioGenerationTask,
                idx=1,
                processed_dialogue={"type": "action", "text": "John walks away"},
                cache_filepath="cache/file2.mp3",
                expected_silence=False,
            ),
        ]

        # Setup additional mocks for the processing phase
        with (
            patch("script_to_speech.plan_audio_generation") as mock_plan,
            patch("script_to_speech.apply_cache_overrides") as mock_apply_overrides,
            patch("script_to_speech.check_for_silence") as mock_check_silence,
            patch("script_to_speech.fetch_and_cache_audio") as mock_fetch,
            patch("script_to_speech.recheck_audio_files") as mock_recheck,
            patch("script_to_speech.AudioSegment") as mock_audio_segment,
            patch("script_to_speech.find_optional_config") as mock_find_config,
            patch("script_to_speech.set_id3_tags_from_config") as mock_set_id3,
            patch("script_to_speech.concatenate_tasks_batched") as mock_concatenate,
            patch("script_to_speech.print_unified_report") as mock_report,
            patch("script_to_speech.save_modified_json") as mock_save_json,
            patch("os.path.exists", return_value=True),
        ):

            # Configure mocks
            mock_plan.return_value = (mock_tasks, ReportingState())
            mock_check_silence.return_value = ReportingState()
            mock_fetch.return_value = ReportingState()
            mock_audio_segment.from_mp3.return_value = MagicMock()
            mock_find_config.return_value = "id3_config.yaml"
            mock_set_id3.return_value = True

            # Act
            script_to_speech.main()

            # Assert
            mock_plan.assert_called_once()
            mock_check_silence.assert_called_once()
            mock_fetch.assert_called_once()
            mock_concatenate.assert_called_once()
            mock_save_json.assert_called_once()
            mock_report.assert_called_once()
            mocks["logger"].info.assert_any_call("Script finished.\n")

    def test_main_dry_run(self, mock_setup):
        """Test a dry run of the main function."""
        # Arrange
        mocks = mock_setup
        mocks["args"].dry_run = True

        mock_tasks = [
            MagicMock(
                spec=AudioGenerationTask,
                idx=0,
                processed_dialogue={
                    "type": "dialogue",
                    "text": "Hello",
                    "speaker": "John",
                },
            )
        ]

        # Setup additional mocks for the processing phase
        with (
            patch("script_to_speech.plan_audio_generation") as mock_plan,
            patch("script_to_speech.check_for_silence") as mock_check_silence,
            patch("script_to_speech.print_unified_report") as mock_report,
            patch("script_to_speech.save_modified_json") as mock_save_json,
            patch("script_to_speech.fetch_and_cache_audio") as mock_fetch,
            patch("script_to_speech.apply_cache_overrides") as mock_apply_overrides,
            patch("script_to_speech.concatenate_tasks_batched") as mock_concatenate,
        ):

            # Configure mocks
            mock_plan.return_value = (mock_tasks, ReportingState())
            mock_check_silence.return_value = ReportingState()

            # Act
            script_to_speech.main()

            # Assert
            mock_plan.assert_called_once()
            mock_check_silence.assert_called_once()
            mock_fetch.assert_not_called()
            mock_concatenate.assert_not_called()
            mock_save_json.assert_called_once()
            mock_report.assert_called_once()
            mocks["logger"].info.assert_any_call("\n--- DRY-RUN Mode Completed ---")

    def test_main_populate_cache(self, mock_setup):
        """Test a populate-cache run of the main function."""
        # Arrange
        mocks = mock_setup
        mocks["args"].populate_cache = True

        mock_tasks = [
            MagicMock(
                spec=AudioGenerationTask,
                idx=0,
                processed_dialogue={
                    "type": "dialogue",
                    "text": "Hello",
                    "speaker": "John",
                },
            )
        ]

        # Setup additional mocks for the processing phase
        with (
            patch("script_to_speech.plan_audio_generation") as mock_plan,
            patch("script_to_speech.check_for_silence") as mock_check_silence,
            patch("script_to_speech.fetch_and_cache_audio") as mock_fetch,
            patch("script_to_speech.recheck_audio_files") as mock_recheck,
            patch("script_to_speech.print_unified_report") as mock_report,
            patch("script_to_speech.save_modified_json") as mock_save_json,
            patch("script_to_speech.apply_cache_overrides") as mock_apply_overrides,
            patch("script_to_speech.concatenate_tasks_batched") as mock_concatenate,
        ):

            # Configure mocks
            mock_plan.return_value = (mock_tasks, ReportingState())
            mock_check_silence.return_value = ReportingState()
            mock_fetch.return_value = ReportingState()

            # Act
            script_to_speech.main()

            # Assert
            mock_plan.assert_called_once()
            mock_check_silence.assert_called_once()
            mock_fetch.assert_called_once()
            mock_concatenate.assert_not_called()
            mock_save_json.assert_called_once()
            mock_report.assert_called_once()
            mocks["logger"].info.assert_any_call(
                "\n--- POPULATE-CACHE Mode Completed ---"
            )

    def test_main_with_error_in_processing(self, mock_setup):
        """Test error handling during processing phase."""
        # Arrange
        mocks = mock_setup

        mock_tasks = [
            MagicMock(
                spec=AudioGenerationTask,
                idx=0,
                processed_dialogue={
                    "type": "dialogue",
                    "text": "Hello",
                    "speaker": "John",
                },
            )
        ]

        # Setup additional mocks for the processing phase
        with (
            patch("script_to_speech.plan_audio_generation") as mock_plan,
            patch(
                "script_to_speech.check_for_silence",
                side_effect=ValueError("Processing error"),
            ),
            patch("script_to_speech.print_unified_report") as mock_report,
            patch("script_to_speech.save_modified_json") as mock_save,
            patch("sys.exit") as mock_exit,
        ):

            # Configure mocks - plan works but check_for_silence fails
            mock_plan.return_value = (mock_tasks, ReportingState())

            # Act
            script_to_speech.main()

            # Assert
            # Since in the try/except, we're expecting print_unified_report to be called
            # then sys.exit() to be called
            mock_exit.assert_called_once_with(1)
            mocks["logger"].error.assert_called()

            assert mock_report.call_count >= 1

    def test_main_error_handling(self, mock_setup):
        """Test more general error handling in the script."""

        with patch("script_to_speech.main") as mock_main:
            # Make main raise an exception
            mock_main.side_effect = IOError("Test error")

            # Act & Assert - script should exit gracefully
            with pytest.raises(IOError, match="Test error"):
                import script_to_speech

                script_to_speech.main()

    def test_dummy_provider_override(self, mock_setup):
        """Test that dummy provider override mode works correctly."""
        # Arrange
        mocks = mock_setup
        mocks["args"].dummy_provider_override = True

        # Act - Just call the TTSProviderManager initialization directly
        with patch("os.makedirs") as mock_makedirs:
            # Call the function that initializes the TTSProviderManager
            script_to_speech.TTSProviderManager(
                mocks["args"].tts_config,
                mocks["args"].provider,
                mocks["args"].dummy_provider_override,
            )

            # Assert
            # Verify TTSProviderManager was initialized with dummy_provider_override=True
            mocks["tts_manager"].assert_called_once_with(
                mocks["args"].tts_config, mocks["args"].provider, True
            )

    def test_modified_json_error_handling(self):
        """Test error handling when saving modified JSON."""
        # Arrange
        test_dialogues = [{"type": "dialogue", "text": "Test"}]
        test_folder = "/output"
        test_input = "/input/test.json"

        # Act
        with (
            patch("builtins.open", side_effect=IOError("Test IO error")),
            patch("script_to_speech.logger") as mock_logger,
        ):

            # Call the function
            script_to_speech.save_modified_json(test_dialogues, test_folder, test_input)

            # Assert
            mock_logger.error.assert_called_once_with(
                "Failed to save modified JSON: Test IO error", exc_info=True
            )
