"""
Unit tests specifically for the check_audio_silence function in the audio_generation.processing module.

This module tests the audio silence detection logic which is critical for identifying
silent audio clips during the audio generation process.
"""

from unittest.mock import MagicMock, patch

import pytest

from audio_generation.models import AudioGenerationTask, ReportingState
from audio_generation.processing import check_audio_silence


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
    )


@pytest.fixture
def mock_logger():
    """Fixture providing a mock logger."""
    with patch("audio_generation.processing.logger") as mock:
        yield mock


@patch("audio_generation.processing.check_audio_level")
def test_silent_clip(mock_check_level, silence_task, mock_logger):
    """Test checking a clip that is silent."""
    # Setup mock to indicate audio is silent
    mock_check_level.return_value = -60.0  # Very low level

    # Initialize reporting state
    reporting_state = ReportingState()

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


@patch("audio_generation.processing.check_audio_level")
def test_non_silent_clip(mock_check_level, silence_task, mock_logger):
    """Test checking a clip that is not silent."""
    # Setup mock to indicate audio is not silent
    mock_check_level.return_value = -20.0  # Higher level

    # Initialize reporting state
    reporting_state = ReportingState()

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


@patch("audio_generation.processing.check_audio_level")
def test_expected_silence_skipped(mock_check_level, expected_silence_task, mock_logger):
    """Test that expected silence tasks are skipped."""
    # Call function
    reporting_state = ReportingState()
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


@patch("audio_generation.processing.check_audio_level")
def test_with_log_prefix(mock_check_level, silence_task, mock_logger):
    """Test logging with a prefix."""
    # Setup mock
    mock_check_level.return_value = -60.0

    # Call with log prefix
    reporting_state = ReportingState()
    check_audio_silence(
        task=silence_task,
        audio_data=b"audio_data",
        silence_threshold=-40.0,
        reporting_state=reporting_state,
        log_prefix="PREFIX: ",
    )

    # Verify prefix was used in logging
    for call_args in mock_logger.debug.call_args_list:
        args, kwargs = call_args
        if args and isinstance(args[0], str) and args[0].startswith("PREFIX:"):
            assert True
            return

    # If we get here, no log messages with the prefix were found
    assert False, "No log messages with the specified prefix were found"


@patch("audio_generation.processing.check_audio_level")
def test_none_level_handled(mock_check_level, silence_task, mock_logger):
    """Test handling of None returned from check_audio_level."""
    # Setup mock to return None (indicating error checking level)
    mock_check_level.return_value = None

    # Initialize reporting state
    reporting_state = ReportingState()

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
