"""
Unit tests for the audio_generation.reporting module.

This module tests the reporting functions used in the audio generation process,
ensuring they correctly handle and present information about audio tasks,
silent clips, and cache misses.
"""

import logging
import os
from collections import defaultdict
from unittest.mock import MagicMock, call, patch

import pytest

from script_to_speech.audio_generation.models import (
    AudioClipInfo,
    AudioGenerationTask,
    ReportingState,
)
from script_to_speech.audio_generation.reporting import (
    print_audio_task_details,
    print_unified_report,
    recheck_audio_files,
)


@pytest.fixture
def sample_task():
    """Fixture providing a sample AudioGenerationTask for testing."""
    return AudioGenerationTask(
        idx=1,
        original_dialogue={
            "type": "dialogue",
            "speaker": "JOHN",
            "text": "Hello world.",
        },
        processed_dialogue={
            "type": "dialogue",
            "speaker": "JOHN",
            "text": "Hello world!",
        },
        text_to_speak="Hello world!",
        speaker="JOHN",
        provider_id="elevenlabs",
        speaker_id="voice_id_123",
        speaker_display="JOHN",
        cache_filename="hash1~~hash2~~elevenlabs~~voice_id_123.mp3",
        cache_filepath="/path/to/cache/hash1~~hash2~~elevenlabs~~voice_id_123.mp3",
        is_cache_hit=True,
        checked_silence_level=-30.5,
    )


@pytest.fixture
def sample_reporting_state():
    """Fixture providing a sample ReportingState for testing."""
    state = ReportingState()

    # Add a silent clip
    state.silent_clips["silent.mp3"] = AudioClipInfo(
        text="Whispered text",
        cache_path="silent.mp3",
        dbfs_level=-60.0,
        speaker_display="JOHN",
        speaker_id="voice_id_123",
        provider_id="elevenlabs",
    )

    # Add a cache miss
    state.cache_misses["missing.mp3"] = AudioClipInfo(
        text="Missing text",
        cache_path="missing.mp3",
        speaker_display="MARY",
        speaker_id="voice_id_456",
        provider_id="openai",
    )

    return state


class TestPrintAudioTaskDetails:
    """Tests for print_audio_task_details function."""

    def test_print_task_details(self, sample_task):
        """Test printing details of an audio task."""
        mock_logger = MagicMock()

        # Call function
        print_audio_task_details(sample_task, mock_logger)

        # Verify log calls
        mock_logger.debug.assert_any_call("Dialogue #: 1")
        mock_logger.debug.assert_any_call("Speaker: JOHN, Type: dialogue")
        mock_logger.debug.assert_any_call("Text: Hello world!")
        mock_logger.debug.assert_any_call("Provider ID: elevenlabs")
        mock_logger.debug.assert_any_call("Speaker ID: voice_id_123")
        mock_logger.debug.assert_any_call(
            "Cache filepath: /path/to/cache/hash1~~hash2~~elevenlabs~~voice_id_123.mp3"
        )
        mock_logger.debug.assert_any_call("Cache hit: True")
        mock_logger.debug.assert_any_call("Audio level (dBFS): -30.5")

        # Verify compact summary log
        found = any(
            "[0001][cache hit][JOHN][Hello world!]" in str(call)
            for call in mock_logger.debug.call_args_list
        )
        assert (
            found
        ), "Expected summary log '[0001][cache hit][JOHN][Hello world!]' not found in debug logs"

    def test_print_task_details_with_log_prefix(self, sample_task):
        """Test printing details with a log prefix."""
        mock_logger = MagicMock()

        # Call function with log prefix
        print_audio_task_details(sample_task, mock_logger, log_prefix="  ")

        # Verify log calls have prefix
        mock_logger.debug.assert_any_call("  Dialogue #: 1")
        mock_logger.debug.assert_any_call("  Speaker: JOHN, Type: dialogue")

    def test_print_task_details_with_truncation(self, sample_task):
        """Test printing with text truncation."""
        mock_logger = MagicMock()

        # Call function with custom max_text_length
        print_audio_task_details(sample_task, mock_logger, max_text_length=5)

        # Verify truncated text in logs (should be in debug, not info)
        found = any(
            "[0001][cache hit][JOHN][He...]" in str(call)
            for call in mock_logger.debug.call_args_list
        )
        assert (
            found
        ), "Expected truncated summary log '[0001][cache hit][JOHN][He...]' not found in debug logs"


class TestRecheckAudioFiles:
    """Tests for recheck_audio_files function."""

    @pytest.fixture
    def mock_logger(self):
        """Fixture providing a mock logger."""
        return MagicMock()

    @patch("os.listdir")
    @patch("os.path.exists")
    @patch("script_to_speech.audio_generation.reporting.check_audio_level")
    def test_recheck_existing_silent_clip_still_silent(
        self,
        mock_check_level,
        mock_exists,
        mock_listdir,
        sample_reporting_state,
        mock_logger,
    ):
        """Test rechecking a silent clip that is still silent."""
        # Setup mocks
        mock_listdir.return_value = ["silent.mp3"]
        mock_exists.return_value = True
        mock_check_level.return_value = -65.0  # Even more silent

        # Mock open file
        mock_open = MagicMock()
        mock_open.return_value.__enter__.return_value.read.return_value = b"audio data"

        with patch("builtins.open", mock_open):
            # Call function
            recheck_audio_files(
                sample_reporting_state, "/path/to/cache", -40.0, mock_logger
            )

        # Verify silent clip is still tracked with updated level
        assert "silent.mp3" in sample_reporting_state.silent_clips
        assert sample_reporting_state.silent_clips["silent.mp3"].dbfs_level == -65.0

    @patch("os.listdir")
    @patch("os.path.exists")
    @patch("script_to_speech.audio_generation.reporting.check_audio_level")
    def test_recheck_existing_silent_clip_no_longer_silent(
        self,
        mock_check_level,
        mock_exists,
        mock_listdir,
        sample_reporting_state,
        mock_logger,
    ):
        """Test rechecking a silent clip that is no longer silent."""
        # Setup mocks
        mock_listdir.return_value = ["silent.mp3"]
        mock_exists.return_value = True
        mock_check_level.return_value = -30.0  # Not silent anymore

        # Mock open file
        mock_open = MagicMock()
        mock_open.return_value.__enter__.return_value.read.return_value = b"audio data"

        with patch("builtins.open", mock_open):
            # Call function
            recheck_audio_files(
                sample_reporting_state, "/path/to/cache", -40.0, mock_logger
            )

        # Verify silent clip is no longer tracked
        assert "silent.mp3" not in sample_reporting_state.silent_clips

    @patch("os.listdir")
    def test_recheck_missing_silent_clip(
        self, mock_listdir, sample_reporting_state, mock_logger
    ):
        """Test rechecking when a previously silent clip is now missing."""
        # Setup mock to indicate files don't exist
        mock_listdir.return_value = []

        # Make a copy of the silent clip info for verification later
        silent_clip_info = sample_reporting_state.silent_clips["silent.mp3"]

        # Call function
        recheck_audio_files(
            sample_reporting_state, "/path/to/cache", -40.0, mock_logger
        )

        # Verify silent clip is no longer tracked but added to cache misses
        assert "silent.mp3" not in sample_reporting_state.silent_clips
        assert "silent.mp3" in sample_reporting_state.cache_misses
        # Verify the cache miss has the same info as the original silent clip
        assert (
            sample_reporting_state.cache_misses["silent.mp3"].text
            == silent_clip_info.text
        )
        assert (
            sample_reporting_state.cache_misses["silent.mp3"].speaker_display
            == silent_clip_info.speaker_display
        )

    @patch("os.listdir")
    def test_recheck_cache_miss_still_missing(
        self, mock_listdir, sample_reporting_state, mock_logger
    ):
        """Test rechecking a cache miss that is still missing."""
        # Setup mock to indicate file doesn't exist
        mock_listdir.return_value = []

        # Call function
        recheck_audio_files(
            sample_reporting_state, "/path/to/cache", -40.0, mock_logger
        )

        # Verify cache miss is still tracked
        assert "missing.mp3" in sample_reporting_state.cache_misses

    @patch("os.listdir")
    def test_recheck_cache_miss_now_exists(
        self, mock_listdir, sample_reporting_state, mock_logger
    ):
        """Test rechecking a cache miss that now exists."""
        # Setup mock to indicate file now exists
        mock_listdir.return_value = ["missing.mp3"]

        # Call function
        recheck_audio_files(
            sample_reporting_state, "/path/to/cache", -40.0, mock_logger
        )

        # Verify cache miss is no longer tracked
        assert "missing.mp3" not in sample_reporting_state.cache_misses

    @patch("os.listdir")
    def test_recheck_handles_missing_cache_folder(
        self, mock_listdir, sample_reporting_state, mock_logger
    ):
        """Test handling of missing cache folder during recheck."""
        # Setup mock to raise FileNotFoundError
        mock_listdir.side_effect = FileNotFoundError("No such directory")

        # Create a copy of the initial state for comparison
        initial_silent_clips = list(sample_reporting_state.silent_clips.keys())
        initial_cache_misses = list(sample_reporting_state.cache_misses.keys())

        # Call function
        recheck_audio_files(
            sample_reporting_state, "/path/to/missing/cache", -40.0, mock_logger
        )

        # Verify warning logged
        mock_logger.warning.assert_called_with(
            "Cache folder /path/to/missing/cache not found during recheck."
        )

        # With no files found, all silent clips should be moved to cache misses
        for clip in initial_silent_clips:
            assert clip not in sample_reporting_state.silent_clips
            assert clip in sample_reporting_state.cache_misses

        # Original cache misses should still be present
        for miss in initial_cache_misses:
            assert miss in sample_reporting_state.cache_misses


class TestPrintUnifiedReport:
    """Tests for print_unified_report function."""

    @pytest.fixture
    def mock_logger(self):
        """Fixture providing a mock logger."""
        return MagicMock()

    @pytest.fixture
    def mock_tts_manager(self):
        """Fixture providing a mock TTSProviderManager."""
        mock = MagicMock()
        return mock

    def test_print_report_with_no_issues(self, mock_logger, mock_tts_manager):
        """Test printing report when there are no issues."""
        # Create empty reporting state
        state = ReportingState()

        # Call function
        print_unified_report(state, mock_logger, mock_tts_manager)

        # Verify "all cached" message
        mock_logger.info.assert_any_call(
            "\nAll audio clips are cached. No additional audio generation needed\n"
        )

    def test_print_report_with_silent_clips(
        self, mock_logger, mock_tts_manager, sample_reporting_state
    ):
        """Test printing report with silent clips."""
        # Call function with silence checking enabled
        print_unified_report(
            sample_reporting_state,
            mock_logger,
            mock_tts_manager,
            silence_checking_enabled=True,
        )

        # Verify silent clips section (less brittle: check substring in any info call)
        found = any(
            "Silent clips detected:" in str(call)
            for call in mock_logger.info.call_args_list
        )
        assert found, "Expected 'Silent clips detected:' section not found in info logs"
        found = any(
            "- JOHN (voice_id_123): 1 clips" in str(call)
            for call in mock_logger.info.call_args_list
        )
        assert found, "Expected '- JOHN (voice_id_123): 1 clips' not found in info logs"
        found = any(
            '• Text: "Whispered text"' in str(call)
            for call in mock_logger.info.call_args_list
        )
        assert found, "Expected '• Text: \"Whispered text\"' not found in info logs"
        found = any(
            "Cache: silent.mp3" in str(call) for call in mock_logger.info.call_args_list
        )
        assert found, "Expected 'Cache: silent.mp3' not found in info logs"
        found = any(
            "dBFS: -60.0" in str(call) for call in mock_logger.info.call_args_list
        )
        assert found, "Expected 'dBFS: -60.0' not found in info logs"

        # Verify summary
        mock_logger.info.assert_any_call("\nSummary:")
        mock_logger.info.assert_any_call("- Silent clips: 1")

    def test_print_report_with_cache_misses(
        self, mock_logger, mock_tts_manager, sample_reporting_state
    ):
        """Test printing report with cache misses."""
        # Call function with silence checking disabled
        print_unified_report(
            sample_reporting_state,
            mock_logger,
            mock_tts_manager,
            silence_checking_enabled=False,
        )

        # Verify cache misses section
        mock_logger.info.assert_any_call(
            "\nCache misses (audio that would need to be generated):"
        )
        mock_logger.info.assert_any_call("\n- MARY (voice_id_456): 1 clips")
        mock_logger.info.assert_any_call('  • Text: "Missing text"')
        mock_logger.info.assert_any_call("    Cache: missing.mp3")

        # Verify summary
        mock_logger.info.assert_any_call("\nSummary:")
        mock_logger.info.assert_any_call("- Cache misses: 1")
        mock_logger.info.assert_any_call(
            "- Total characters to generate: 12"
        )  # Length of "Missing text"

    def test_print_report_with_both_issues(
        self, mock_logger, mock_tts_manager, sample_reporting_state
    ):
        """Test printing report with both silent clips and cache misses."""
        # Call function with silence checking enabled
        print_unified_report(
            sample_reporting_state,
            mock_logger,
            mock_tts_manager,
            silence_checking_enabled=True,
        )

        # Verify both sections are included (less brittle: check substring in any info call)
        found = any(
            "Silent clips detected:" in str(call)
            for call in mock_logger.info.call_args_list
        )
        assert found, "Expected 'Silent clips detected:' section not found in info logs"
        found = any(
            "Additional cache misses" in str(call)
            for call in mock_logger.info.call_args_list
        )
        assert (
            found
        ), "Expected 'Additional cache misses' section not found in info logs"

        # Verify summary includes both
        mock_logger.info.assert_any_call("- Silent clips: 1")
        mock_logger.info.assert_any_call("- Cache misses: 1")

    @patch("script_to_speech.audio_generation.reporting.get_command_string")
    def test_print_report_with_command_generation(
        self, mock_get_command, mock_logger, mock_tts_manager, sample_reporting_state
    ):
        """Test command generation in the report."""
        # Setup mock for command string
        mock_get_command.return_value = (
            "python generate_speech.py --voice=voice_id_123 --text='Missing text'"
        )

        # Call function
        print_unified_report(
            sample_reporting_state,
            mock_logger,
            mock_tts_manager,
            silence_checking_enabled=True,
            max_misses_to_report=10,
        )

        # Verify commands section
        mock_logger.info.assert_any_call("\nCommands to generate missing audio clips:")
        mock_logger.info.assert_any_call(
            "\n# 1 clips for elevenlabs voice voice_id_123 (JOHN):"
        )
        mock_logger.info.assert_any_call(
            "python generate_speech.py --voice=voice_id_123 --text='Missing text'"
        )

    def test_print_report_with_too_many_misses(self, mock_logger, mock_tts_manager):
        """Test report with more misses than the reporting limit."""
        # Create state with many misses
        state = ReportingState()
        for i in range(30):  # Add 30 misses
            state.cache_misses[f"missing{i}.mp3"] = AudioClipInfo(
                text=f"Text{i}",
                cache_path=f"missing{i}.mp3",
                speaker_display="JOHN",
                speaker_id="voice_id_123",
                provider_id="elevenlabs",
            )

        # Call function with low limit
        print_unified_report(
            state,
            mock_logger,
            mock_tts_manager,
            silence_checking_enabled=False,
            max_misses_to_report=10,
        )

        # Verify warning about too many misses
        mock_logger.info.assert_any_call(
            "\nToo many misses to show commands (30 total)."
        )
        mock_logger.info.assert_any_call(
            "Use a higher --max-misses-to-report value to see more."
        )

    def test_print_report_with_text_length_filter(self, mock_logger, mock_tts_manager):
        """Test text length filtering for command generation."""
        # Create state with texts of different lengths
        state = ReportingState()
        # Short text (will be included)
        state.cache_misses["short.mp3"] = AudioClipInfo(
            text="Short",
            cache_path="short.mp3",
            speaker_display="JOHN",
            speaker_id="voice_id_123",
            provider_id="elevenlabs",
        )
        # Long text (will be excluded)
        state.cache_misses["long.mp3"] = AudioClipInfo(
            text="This is a very long text that exceeds the maximum length limit",
            cache_path="long.mp3",
            speaker_display="JOHN",
            speaker_id="voice_id_123",
            provider_id="elevenlabs",
        )

        # Call function with mock command generation
        with patch(
            "script_to_speech.audio_generation.reporting.get_command_string"
        ) as mock_get_command:
            mock_get_command.return_value = (
                "python generate_speech.py --voice=voice_id_123 --text='Short'"
            )

            print_unified_report(
                state,
                mock_logger,
                mock_tts_manager,
                silence_checking_enabled=False,
                max_text_length=10,
            )

            # Verify command generation was called only for the short text
            mock_get_command.assert_called_once()
            # First arg is tts_manager, second is speaker display, third is texts list
            assert mock_get_command.call_args[0][2] == ["Short"]
