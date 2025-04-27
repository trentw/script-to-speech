"""
Tests for the dummy provider override functionality.

This module tests the ability to override configured providers with dummy providers
for testing purposes.
"""

import os
import tempfile
from unittest.mock import patch

import pytest
import yaml

from tts_providers.tts_provider_manager import TTSProviderManager


class TestDummyProviderOverride:
    """Tests for the dummy provider override functionality."""

    @pytest.fixture
    def sample_config_file(self):
        """Create a temporary config file with non-dummy providers."""
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

        yield temp_path

        # Cleanup
        if os.path.exists(temp_path):
            os.remove(temp_path)

    def test_dummy_provider_override_enabled(self, sample_config_file):
        """Test that providers are correctly overridden when dummy_provider_override is True."""
        # Initialize TTSProviderManager with dummy_provider_override=True
        manager = TTSProviderManager(sample_config_file, dummy_provider_override=True)

        # Ensure the manager is initialized
        manager._ensure_initialized()

        # Check that the providers have been swapped to dummy providers
        assert manager._speaker_providers["default"] == "dummy_stateless"
        assert manager._speaker_providers["JOHN"] == "dummy_stateful"

        # Check that dummy_id was added to the configs
        assert "dummy_id" in manager._speaker_configs_map["default"]
        assert manager._speaker_configs_map["default"]["dummy_id"] == "alloy"

        assert "dummy_id" in manager._speaker_configs_map["JOHN"]
        assert manager._speaker_configs_map["JOHN"]["dummy_id"] == "some-voice-id"

    def test_dummy_provider_override_disabled(self, sample_config_file):
        """Test that providers are not overridden when dummy_provider_override is False."""
        # Initialize TTSProviderManager with dummy_provider_override=False (default)
        manager = TTSProviderManager(sample_config_file)

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
        import script_to_speech

        # Mock the parse_arguments function to return args with dummy_provider_override=True
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
            patch("script_to_speech.plan_audio_generation") as mock_plan,
            patch("script_to_speech.print_unified_report") as mock_report,
            patch("script_to_speech.save_modified_json") as mock_save_json,
            patch("os.makedirs") as mock_makedirs,
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
            args.tts_config = sample_config_file
            args.provider = None
            args.processor_configs = None
            args.ffmpeg_path = None
            args.max_report_misses = 20
            args.max_report_text = 30
            args.dummy_provider_override = True
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
                {"type": "dialogue", "text": "Hello", "speaker": "JOHN"},
            ]

            # Configure plan_audio_generation mock
            from unittest.mock import MagicMock

            from audio_generation.models import AudioGenerationTask, ReportingState

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
            # Check that TTSProviderManager was initialized with dummy_provider_override=True
            mock_tts_manager.assert_called_once_with(sample_config_file, None, True)

            # Check that create_output_folders was called with dummy_provider_override=True
            mock_create_folders.assert_called_once_with(
                args.input_file, "dry-run", True  # dummy_provider_override
            )
