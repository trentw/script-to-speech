"""
Unit tests for the fetch_and_cache_audio function in the audio_generation.processing module.

This module tests the functionality for fetching and caching audio clips during the
audio generation process.
"""

import io
from unittest.mock import MagicMock, patch

import pytest
from pydub import AudioSegment

from audio_generation.models import AudioClipInfo, AudioGenerationTask, ReportingState
from audio_generation.processing import (
    fetch_and_cache_audio,
    update_cache_duplicate_state,
)


@pytest.fixture
def mock_tts_provider_manager():
    """Fixture providing a mock TTSProviderManager."""
    mock = MagicMock()

    # Setup mock methods
    mock.get_provider_for_speaker.side_effect = lambda speaker: (
        "elevenlabs" if speaker == "JOHN" else "openai"
    )
    mock.get_speaker_identifier.side_effect = lambda speaker: (
        "voice_id_123" if speaker == "JOHN" else "voice_id_456"
    )
    mock.generate_audio.return_value = b"audio_data"

    return mock


@pytest.fixture
def mock_logger():
    """Fixture providing a mock logger."""
    with patch("audio_generation.processing.logger") as mock:
        yield mock


@pytest.fixture
def fetch_tasks():
    """Fixture providing sample tasks for fetching."""
    return [
        # Cache hit that should be skipped
        AudioGenerationTask(
            idx=0,
            original_dialogue={
                "type": "dialog",
                "speaker": "JOHN",
                "text": "Already cached",
            },
            processed_dialogue={
                "type": "dialog",
                "speaker": "JOHN",
                "text": "Already cached!",
            },
            text_to_speak="Already cached!",
            speaker="JOHN",
            provider_id="elevenlabs",
            speaker_id="voice_id_123",
            speaker_display="JOHN",
            cache_filename="cached~~cached~~elevenlabs~~voice_id_123.mp3",
            cache_filepath="/path/to/cache/cached~~cached~~elevenlabs~~voice_id_123.mp3",
            is_cache_hit=True,
            expected_silence=False,
        ),
        # Cache miss that needs to be generated
        AudioGenerationTask(
            idx=1,
            original_dialogue={
                "type": "dialog",
                "speaker": "MARY",
                "text": "Generate me",
            },
            processed_dialogue={
                "type": "dialog",
                "speaker": "MARY",
                "text": "Generate me!",
            },
            text_to_speak="Generate me!",
            speaker="MARY",
            provider_id="openai",
            speaker_id="voice_id_456",
            speaker_display="MARY",
            cache_filename="missing~~missing~~openai~~voice_id_456.mp3",
            cache_filepath="/path/to/cache/missing~~missing~~openai~~voice_id_456.mp3",
            is_cache_hit=False,
            expected_silence=False,
        ),
        # Empty text that should generate a silent clip
        AudioGenerationTask(
            idx=2,
            original_dialogue={"type": "dialog", "speaker": None, "text": ""},
            processed_dialogue={"type": "dialog", "speaker": None, "text": ""},
            text_to_speak="",
            speaker=None,
            provider_id="elevenlabs",
            speaker_id=None,
            speaker_display="(default)",
            cache_filename="empty~~empty~~elevenlabs~~none.mp3",
            cache_filepath="/path/to/cache/empty~~empty~~elevenlabs~~none.mp3",
            is_cache_hit=False,
            expected_silence=True,
        ),
    ]


@pytest.fixture
def fetch_tasks_with_duplicates():
    """Fixture providing sample tasks with duplicate cache filepaths."""
    return [
        # Cache hit that should be skipped
        AudioGenerationTask(
            idx=0,
            original_dialogue={
                "type": "dialog",
                "speaker": "JOHN",
                "text": "Already cached",
            },
            processed_dialogue={
                "type": "dialog",
                "speaker": "JOHN",
                "text": "Already cached!",
            },
            text_to_speak="Already cached!",
            speaker="JOHN",
            provider_id="elevenlabs",
            speaker_id="voice_id_123",
            speaker_display="JOHN",
            cache_filename="cached~~cached~~elevenlabs~~voice_id_123.mp3",
            cache_filepath="/path/to/cache/cached~~cached~~elevenlabs~~voice_id_123.mp3",
            is_cache_hit=True,
            expected_silence=False,
            expected_cache_duplicate=False,
        ),
        # Two tasks with the same cache filepath
        AudioGenerationTask(
            idx=1,
            original_dialogue={
                "type": "dialog",
                "speaker": "MARY",
                "text": "Duplicate path 1",
            },
            processed_dialogue={
                "type": "dialog",
                "speaker": "MARY",
                "text": "Duplicate path 1!",
            },
            text_to_speak="Duplicate path 1!",
            speaker="MARY",
            provider_id="openai",
            speaker_id="voice_id_456",
            speaker_display="MARY",
            cache_filename="dupe~~dupe~~openai~~voice_id_456.mp3",
            cache_filepath="/path/to/cache/dupe~~dupe~~openai~~voice_id_456.mp3",
            is_cache_hit=False,
            expected_silence=False,
            expected_cache_duplicate=False,  # Will be updated by the function
        ),
        AudioGenerationTask(
            idx=2,
            original_dialogue={
                "type": "dialog",
                "speaker": "BOB",
                "text": "Duplicate path 2",
            },
            processed_dialogue={
                "type": "dialog",
                "speaker": "BOB",
                "text": "Duplicate path 2!",
            },
            text_to_speak="Duplicate path 2!",
            speaker="BOB",
            provider_id="openai",
            speaker_id="voice_id_456",
            speaker_display="BOB",
            cache_filename="dupe~~dupe~~openai~~voice_id_456.mp3",  # Same as task 1
            cache_filepath="/path/to/cache/dupe~~dupe~~openai~~voice_id_456.mp3",  # Same as task 1
            is_cache_hit=False,
            expected_silence=False,
            expected_cache_duplicate=False,  # Will be updated by the function
        ),
    ]


@patch("audio_generation.processing.update_cache_duplicate_state")
@patch("os.makedirs")
@patch("builtins.open")
def test_fetch_calls_update_duplicate_state(
    mock_open,
    mock_makedirs,
    mock_update_duplicate_state,
    fetch_tasks,
    mock_tts_provider_manager,
    mock_logger,
):
    """Test that fetch_and_cache_audio calls update_cache_duplicate_state."""
    # Arrange
    mock_update_duplicate_state.return_value = 0  # No duplicates for this test

    # Act
    fetch_and_cache_audio(
        tasks=fetch_tasks,
        tts_provider_manager=mock_tts_provider_manager,
        silence_threshold=None,
    )

    # Assert
    mock_update_duplicate_state.assert_called_once_with(fetch_tasks)


@patch("os.makedirs")
@patch("builtins.open")
def test_fetch_skip_cache_hits(
    mock_open, mock_makedirs, fetch_tasks, mock_tts_provider_manager, mock_logger
):
    """Test that cache hits are skipped during fetching."""
    # Arrange - tasks already setup in fixture

    # Act
    reporting_state = fetch_and_cache_audio(
        tasks=fetch_tasks,
        tts_provider_manager=mock_tts_provider_manager,
        silence_threshold=None,
    )

    # Assert
    assert fetch_tasks[0].is_cache_hit is True  # Still a hit
    # Verify TTS provider was not called for the cached task
    assert not any(
        call[0][0] == "JOHN" and call[0][1] == "Already cached!"
        for call in mock_tts_provider_manager.generate_audio.call_args_list
    )


@patch("audio_generation.processing.update_cache_duplicate_state")
@patch("os.makedirs")
@patch("builtins.open")
def test_fetch_skip_duplicate_tasks(
    mock_open,
    mock_makedirs,
    mock_update_duplicate_state,
    fetch_tasks_with_duplicates,
    mock_tts_provider_manager,
    mock_logger,
):
    """Test that duplicate tasks are skipped during fetching."""

    # Arrange
    # Set up the mock to modify tasks (mark second task as duplicate)
    def side_effect(tasks):
        tasks[2].expected_cache_duplicate = True  # Mark task 2 as duplicate
        return 1  # Return count of duplicates

    mock_update_duplicate_state.side_effect = side_effect

    # Act
    reporting_state = fetch_and_cache_audio(
        tasks=fetch_tasks_with_duplicates,
        tts_provider_manager=mock_tts_provider_manager,
        silence_threshold=None,
    )

    # Assert
    # First task is skipped because it's a cache hit
    # Second task is processed normally
    # Third task is skipped because it's marked as a duplicate
    assert (
        mock_tts_provider_manager.generate_audio.call_count == 1
    )  # Only one task should generate audio

    # Check the specific call to generate_audio
    mock_tts_provider_manager.generate_audio.assert_called_once_with(
        "MARY", "Duplicate path 1!"
    )


@patch("audio_generation.processing.update_cache_duplicate_state")
@patch("os.makedirs")
@patch("builtins.open")
def test_fetch_generate_audio(
    mock_open,
    mock_makedirs,
    mock_update_duplicate_state,
    fetch_tasks,
    mock_tts_provider_manager,
    mock_logger,
):
    """Test generating audio for a cache miss."""
    # Arrange
    mock_file = MagicMock()
    mock_open.return_value.__enter__.return_value = mock_file

    # Act
    reporting_state = fetch_and_cache_audio(
        tasks=fetch_tasks,
        tts_provider_manager=mock_tts_provider_manager,
        silence_threshold=None,
    )

    # Assert
    mock_tts_provider_manager.generate_audio.assert_any_call("MARY", "Generate me!")
    mock_file.write.assert_any_call(b"audio_data")
    assert fetch_tasks[1].is_cache_hit is True  # Now a cache hit


@patch("audio_generation.processing.AudioSegment")
@patch("builtins.open")
@patch("os.makedirs")
def test_fetch_generate_silent_audio(
    mock_makedirs,
    mock_open,
    mock_audio_segment,
    fetch_tasks,
    mock_tts_provider_manager,
    mock_logger,
):
    """Test generating silent audio for empty text."""
    # Arrange
    # Setup mock file
    mock_file = MagicMock()
    mock_open.return_value.__enter__.return_value = mock_file

    # Setup silent audio segment
    mock_silent = MagicMock()
    mock_audio_segment.silent.return_value = mock_silent

    # Setup BytesIO to return silent data
    with patch("audio_generation.processing.io.BytesIO") as mock_bytesio:
        mock_buffer = MagicMock()
        mock_bytesio.return_value.__enter__.return_value = mock_buffer
        mock_buffer.getvalue.return_value = b"silent_audio_data"

        # Act
        reporting_state = fetch_and_cache_audio(
            tasks=fetch_tasks,
            tts_provider_manager=mock_tts_provider_manager,
            silence_threshold=None,
        )

    # Assert
    mock_audio_segment.silent.assert_called_once()  # Called for empty text task
    mock_file.write.assert_any_call(b"silent_audio_data")  # Silent audio was written
    assert fetch_tasks[2].is_cache_hit is True  # Now a cache hit


@patch("audio_generation.utils.check_audio_silence")
@patch("builtins.open")
@patch("os.makedirs")
def test_fetch_with_silence_checking(
    mock_makedirs,
    mock_open,
    mock_check_silence,
    fetch_tasks,
    mock_tts_provider_manager,
    mock_logger,
):
    """Test fetch with silence checking enabled."""
    # Arrange
    mock_file = MagicMock()
    mock_open.return_value.__enter__.return_value = mock_file

    # Setup mock to indicate non-silent audio
    mock_check_silence.return_value = False

    # Act
    reporting_state = fetch_and_cache_audio(
        tasks=fetch_tasks,
        tts_provider_manager=mock_tts_provider_manager,
        silence_threshold=-40.0,  # Enable silence checking
    )

    # Assert
    # Should be called only once - since only one non-expected-silent task is generated
    # The expected_silence=True task is skipped in the check_audio_silence function
    assert mock_check_silence.call_count == 1
    assert len(reporting_state.silent_clips) == 0


@patch("os.makedirs")
@patch("builtins.open")
def test_fetch_with_real_duplicate_detection(
    mock_open,
    mock_makedirs,
    fetch_tasks_with_duplicates,
    mock_tts_provider_manager,
    mock_logger,
):
    """Test fetch_and_cache_audio with real duplicate detection logic."""
    # Arrange
    mock_file = MagicMock()
    mock_open.return_value.__enter__.return_value = mock_file

    # Act - using the real update_cache_duplicate_state function
    reporting_state = fetch_and_cache_audio(
        tasks=fetch_tasks_with_duplicates,
        tts_provider_manager=mock_tts_provider_manager,
        silence_threshold=None,
    )

    # Assert
    # First task is skipped (cache hit)
    # Second task is processed
    # Third task is skipped (duplicate)
    assert mock_tts_provider_manager.generate_audio.call_count == 1
    assert (
        fetch_tasks_with_duplicates[1].expected_cache_duplicate is False
    )  # First occurrence not marked
    assert (
        fetch_tasks_with_duplicates[2].expected_cache_duplicate is True
    )  # Duplicate marked
    mock_tts_provider_manager.generate_audio.assert_called_once_with(
        "MARY", "Duplicate path 1!"
    )


@patch("audio_generation.utils.check_audio_silence")
@patch("builtins.open")
@patch("os.makedirs")
def test_fetch_with_silence_detection(
    mock_makedirs,
    mock_open,
    mock_check_silence,
    fetch_tasks,
    mock_tts_provider_manager,
    mock_logger,
):
    """Test fetch detecting silent audio."""
    # Arrange
    mock_file = MagicMock()
    mock_open.return_value.__enter__.return_value = mock_file

    # Setup mock to actually add to the reporting_state.silent_clips
    def mock_check_silence_impl(
        task, audio_data, silence_threshold, reporting_state, log_prefix
    ):
        # Add a silent clip entry to reporting_state for this task
        reporting_state.silent_clips[task.cache_filename] = AudioClipInfo(
            text=task.text_to_speak,
            cache_path=task.cache_filename,
            dbfs_level=-60.0,  # Very silent
            speaker_display=task.speaker_display,
            speaker_id=task.speaker_id,
            provider_id=task.provider_id,
        )
        return True  # Indicate the audio is silent

    mock_check_silence.side_effect = mock_check_silence_impl

    # Act
    reporting_state = fetch_and_cache_audio(
        tasks=fetch_tasks,
        tts_provider_manager=mock_tts_provider_manager,
        silence_threshold=-40.0,  # Enable silence checking
    )

    # Assert
    # Only called once for the non-expected-silent task that gets generated
    assert mock_check_silence.call_count == 1
    assert len(reporting_state.silent_clips) == 1  # One silent clip detected


@patch("builtins.open")
@patch("os.makedirs")
def test_fetch_tts_provider_error(
    mock_makedirs, mock_open, fetch_tasks, mock_tts_provider_manager, mock_logger
):
    """Test handling errors from TTS provider."""
    # Arrange
    mock_file = MagicMock()
    mock_open.return_value.__enter__.return_value = mock_file

    # Setup TTS provider to raise exception
    mock_tts_provider_manager.generate_audio.side_effect = Exception("TTS error")

    # Act
    reporting_state = fetch_and_cache_audio(
        tasks=fetch_tasks,
        tts_provider_manager=mock_tts_provider_manager,
        silence_threshold=None,
    )

    # Assert
    assert fetch_tasks[1].is_cache_hit is False  # Still a miss (generation failed)
    mock_logger.error.assert_called()  # Error was logged


@patch("builtins.open")
@patch("os.makedirs")
def test_fetch_file_write_error(
    mock_makedirs, mock_open, fetch_tasks, mock_tts_provider_manager, mock_logger
):
    """Test handling errors when writing to file."""
    # Arrange
    # Setup open to raise exception
    mock_open.side_effect = Exception("File write error")

    # Act
    reporting_state = fetch_and_cache_audio(
        tasks=fetch_tasks,
        tts_provider_manager=mock_tts_provider_manager,
        silence_threshold=None,
    )

    # Assert
    assert fetch_tasks[1].is_cache_hit is False  # Still a miss (write failed)
    mock_logger.error.assert_called()  # Error was logged
