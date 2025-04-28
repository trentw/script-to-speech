"""
Unit tests specifically for the check_audio_silence function in the audio_generation.processing module.

This module tests the audio silence detection logic which is critical for identifying
silent audio clips during the audio generation process.
"""

from unittest.mock import MagicMock, patch

import pytest

from script_to_speech.audio_generation.models import (
    AudioClipInfo,
    AudioGenerationTask,
    ReportingState,
    TaskStatus,
)
from script_to_speech.audio_generation.utils import check_audio_silence


@pytest.fixture
def silence_task():
    """Fixture providing a task for silence checking."""
    return AudioGenerationTask(
        idx=1,
        original_dialogue={"type": "dialog", "speaker": "JOHN", "text": "Hello"},
        processed_dialogue={"type": "dialog", "speaker": "JOHN", "text": "Hello!"},
        text_to_speak="Hello!",
        speaker="JOHN",
        provider_id="elevenlabs",
        speaker_id="voice_id_123",
        speaker_display="JOHN",
        cache_filename="hash1~~hash2~~elevenlabs~~voice_id_123.mp3",
        cache_filepath="/path/to/cache/hash1~~hash2~~elevenlabs~~voice_id_123.mp3",
        is_cache_hit=True,
        expected_silence=False,
        status=TaskStatus.PENDING,
        retry_count=0,
    )


@pytest.fixture
def expected_silence_task():
    """Fixture providing a task that is expected to be silent."""
    return AudioGenerationTask(
        idx=0,
        original_dialogue={"type": "dialog", "speaker": None, "text": ""},
        processed_dialogue={"type": "dialog", "speaker": None, "text": ""},
        text_to_speak="",
        speaker=None,
        provider_id="elevenlabs",
        speaker_id=None,
        speaker_display="(default)",
        cache_filename="empty~~empty~~elevenlabs~~none.mp3",
        cache_filepath="/path/to/cache/empty~~empty~~elevenlabs~~none.mp3",
        is_cache_hit=True,
        expected_silence=True,
        status=TaskStatus.PENDING,
        retry_count=0,
    )


@pytest.fixture
def mock_logger():
    """Fixture providing a mock logger."""
    with patch("script_to_speech.audio_generation.utils.logger") as mock:
        yield mock


def test_silent_clip(silence_task, mock_logger):
    """Test checking a clip that is silent."""
    # Initialize reporting state
    reporting_state = ReportingState()

    # Mock the check_audio_level function
    with patch("script_to_speech.audio_generation.utils.check_audio_level", return_value=-60.0):
        # Call function
        result = check_audio_silence(
            task=silence_task,
            audio_data=b"audio_data",
            silence_threshold=-40.0,
            reporting_state=reporting_state,
            log_prefix="",
        )

    # Verify result indicates silence
    assert result is True

    # Verify task has level recorded
    assert silence_task.checked_silence_level == -60.0

    # Verify clip was added to reporting state
    assert len(reporting_state.silent_clips) == 1
    assert silence_task.cache_filename in reporting_state.silent_clips
    assert reporting_state.silent_clips[silence_task.cache_filename].dbfs_level == -60.0


def test_non_silent_clip(silence_task, mock_logger):
    """Test checking a clip that is not silent."""
    # Initialize reporting state
    reporting_state = ReportingState()

    # Mock the check_audio_level function
    with patch("script_to_speech.audio_generation.utils.check_audio_level", return_value=-20.0):
        # Call function
        result = check_audio_silence(
            task=silence_task,
            audio_data=b"audio_data",
            silence_threshold=-40.0,
            reporting_state=reporting_state,
            log_prefix="",
        )

    # Verify result indicates not silent
    assert result is False

    # Verify task has level recorded
    assert silence_task.checked_silence_level == -20.0

    # Verify no clips were added to reporting state
    assert len(reporting_state.silent_clips) == 0


def test_expected_silence_skipped(expected_silence_task, mock_logger):
    """Test that expected silence tasks are skipped."""
    # Call function
    reporting_state = ReportingState()

    # This shouldn't call check_audio_level at all
    with patch("script_to_speech.audio_generation.utils.check_audio_level") as mock_check_level:
        result = check_audio_silence(
            task=expected_silence_task,
            audio_data=b"audio_data",
            silence_threshold=-40.0,
            reporting_state=reporting_state,
            log_prefix="",
        )

        # Verify result indicates not silent (because we skip the check)
        assert result is False

        # Verify mock was not called
        mock_check_level.assert_not_called()

    # Verify no clips were added to reporting state
    assert len(reporting_state.silent_clips) == 0


def test_with_log_prefix(silence_task, mock_logger):
    """Test logging with a prefix."""
    # Initialize reporting state
    reporting_state = ReportingState()

    # Mock check_audio_level to return silent level
    with patch("script_to_speech.audio_generation.utils.check_audio_level", return_value=-60.0):
        # Call with log prefix
        check_audio_silence(
            task=silence_task,
            audio_data=b"audio_data",
            silence_threshold=-40.0,
            reporting_state=reporting_state,
            log_prefix="PREFIX: ",
        )

    # Verify prefix was used in logging warn messages
    for call_args in mock_logger.warning.call_args_list:
        args, kwargs = call_args
        if args and isinstance(args[0], str) and args[0].startswith("PREFIX:"):
            assert True
            return

    # If we get here, no log messages with the prefix were found
    assert False, "No log messages with the specified prefix were found"


def test_none_level_handled(silence_task, mock_logger):
    """Test handling of None returned from check_audio_level."""
    # Initialize reporting state
    reporting_state = ReportingState()

    # Mock check_audio_level to return None
    with patch("script_to_speech.audio_generation.utils.check_audio_level", return_value=None):
        # Call function
        result = check_audio_silence(
            task=silence_task,
            audio_data=b"audio_data",
            silence_threshold=-40.0,
            reporting_state=reporting_state,
            log_prefix="",
        )

    # Verify result indicates not silent (since we can't determine)
    assert result is False

    # Verify no clips were added to reporting state
    assert len(reporting_state.silent_clips) == 0
