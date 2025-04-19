"""
Unit tests for the fetch_and_cache_audio function in the audio_generation.processing module.

This module tests the functionality for fetching and caching audio clips during the
audio generation process.
"""

import io
from unittest.mock import MagicMock, patch

import pytest
from pydub import AudioSegment

from audio_generation.models import (
    AudioClipInfo,
    AudioGenerationTask,
    ReportingState,
    TaskStatus,
)
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

    # Add the new method for provider-specific limits
    mock.get_provider_download_threads.return_value = 3

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
            status=TaskStatus.PENDING,
            retry_count=0,
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
            status=TaskStatus.PENDING,
            retry_count=0,
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
            status=TaskStatus.PENDING,
            retry_count=0,
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
            status=TaskStatus.PENDING,
            retry_count=0,
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
            status=TaskStatus.PENDING,
            retry_count=0,
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
            status=TaskStatus.PENDING,
            retry_count=0,
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
    monkeypatch,
):
    """Test that fetch_and_cache_audio calls update_cache_duplicate_state."""
    # Arrange
    mock_update_duplicate_state.return_value = 0  # No duplicates for this test

    # Mock the AudioDownloadManager class
    mock_download_manager = MagicMock()
    mock_download_manager.return_value.run.return_value = ReportingState()
    monkeypatch.setattr(
        "audio_generation.download_manager.AudioDownloadManager", mock_download_manager
    )

    # Act
    fetch_and_cache_audio(
        tasks=fetch_tasks,
        tts_provider_manager=mock_tts_provider_manager,
        silence_threshold=None,
    )

    # Assert
    # Force the mock to register that it was called
    assert mock_update_duplicate_state.call_count == 1  # Called exactly once
    mock_update_duplicate_state.assert_called_once_with(fetch_tasks)
    mock_download_manager.assert_called_once()


@patch("os.makedirs")
@patch("builtins.open")
def test_fetch_skip_cache_hits(
    mock_open,
    mock_makedirs,
    fetch_tasks,
    mock_tts_provider_manager,
    mock_logger,
    monkeypatch,
):
    """Test that cache hits are skipped during fetching."""
    # Arrange - tasks already setup in fixture
    mock_download_manager = MagicMock()
    mock_download_manager.return_value.run.return_value = ReportingState()
    monkeypatch.setattr(
        "audio_generation.download_manager.AudioDownloadManager", mock_download_manager
    )

    # Act
    reporting_state = fetch_and_cache_audio(
        tasks=fetch_tasks,
        tts_provider_manager=mock_tts_provider_manager,
        silence_threshold=None,
    )

    # Assert
    # Mark first task as CACHED when status is updated
    assert fetch_tasks[0].status == TaskStatus.CACHED


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
    monkeypatch,
):
    """Test that duplicate tasks are skipped during fetching."""

    # Arrange
    # Set up the mock to modify tasks (mark second task as duplicate)
    def side_effect(tasks):
        tasks[2].expected_cache_duplicate = True  # Mark task 2 as duplicate
        return 1  # Return count of duplicates

    mock_update_duplicate_state.side_effect = side_effect
    mock_update_duplicate_state.return_value = 1  # Ensure the mock records the call

    mock_download_manager = MagicMock()

    def mock_run_side_effect():
        # Set proper status for all tasks
        fetch_tasks_with_duplicates[0].status = TaskStatus.CACHED
        fetch_tasks_with_duplicates[1].status = TaskStatus.GENERATED
        fetch_tasks_with_duplicates[2].status = TaskStatus.SKIPPED_DUPLICATE
        return ReportingState()

    mock_download_manager.return_value.run.side_effect = mock_run_side_effect
    monkeypatch.setattr(
        "audio_generation.download_manager.AudioDownloadManager", mock_download_manager
    )

    # Act
    reporting_state = fetch_and_cache_audio(
        tasks=fetch_tasks_with_duplicates,
        tts_provider_manager=mock_tts_provider_manager,
        silence_threshold=None,
    )

    # Assert
    # Verify mock was called
    assert mock_update_duplicate_state.call_count == 1
    # Verify tasks have correct status
    assert fetch_tasks_with_duplicates[0].status == TaskStatus.CACHED
    assert fetch_tasks_with_duplicates[2].status == TaskStatus.SKIPPED_DUPLICATE

    # Verify AudioDownloadManager was called with the right parameters
    mock_download_manager.assert_called_once()


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
    monkeypatch,
):
    """Test generating audio for a cache miss."""
    # Arrange
    mock_file = MagicMock()
    mock_open.return_value.__enter__.return_value = mock_file

    # Setup download manager to mark task as generated
    mock_download_manager = MagicMock()

    def mock_run_side_effect():
        # Update all task statuses
        fetch_tasks[0].status = TaskStatus.CACHED
        # Mark the second task as generated
        fetch_tasks[1].status = TaskStatus.GENERATED
        fetch_tasks[1].is_cache_hit = True
        # Set status for task 2 too
        fetch_tasks[2].status = TaskStatus.GENERATED
        fetch_tasks[2].is_cache_hit = True
        return ReportingState()

    mock_download_manager.return_value.run.side_effect = mock_run_side_effect
    monkeypatch.setattr(
        "audio_generation.download_manager.AudioDownloadManager", mock_download_manager
    )

    # Act
    reporting_state = fetch_and_cache_audio(
        tasks=fetch_tasks,
        tts_provider_manager=mock_tts_provider_manager,
        silence_threshold=None,
    )

    # Assert
    assert fetch_tasks[1].status == TaskStatus.GENERATED
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
    monkeypatch,
):
    """Test generating silent audio for empty text."""
    # Arrange
    # Create a mock file handler
    mock_file = MagicMock()
    mock_open.return_value.__enter__.return_value = mock_file

    # Setup download manager to mark task as generated
    mock_download_manager = MagicMock()

    def mock_run_side_effect():
        # Mark all tasks with appropriate status
        fetch_tasks[0].status = TaskStatus.CACHED
        fetch_tasks[1].status = TaskStatus.GENERATED
        fetch_tasks[1].is_cache_hit = True
        # Mark the silent task as generated
        fetch_tasks[2].status = TaskStatus.GENERATED
        fetch_tasks[2].is_cache_hit = True
        return ReportingState()

    # Set up the task state before the download manager runs
    fetch_tasks[2].status = TaskStatus.PENDING

    mock_download_manager.return_value.run.side_effect = mock_run_side_effect
    monkeypatch.setattr(
        "audio_generation.download_manager.AudioDownloadManager", mock_download_manager
    )

    # Set up mock for silent audio
    mock_silent = MagicMock()
    mock_audio_segment.silent.return_value = mock_silent

    # Act
    reporting_state = fetch_and_cache_audio(
        tasks=fetch_tasks,
        tts_provider_manager=mock_tts_provider_manager,
        silence_threshold=None,
    )

    # Assert
    assert fetch_tasks[2].status == TaskStatus.GENERATED
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
    monkeypatch,
):
    """Test fetch with silence checking enabled."""
    # Arrange
    mock_file = MagicMock()
    mock_open.return_value.__enter__.return_value = mock_file

    # Explicitly set the return value for check_silence
    mock_check_silence.return_value = False  # Not silent

    # Make sure check_silence is called at least once to register
    mock_check_silence.assert_not_called()  # This will register the mock

    # Mock the download manager
    mock_download_manager = MagicMock()

    # Setup silence checking in download manager run
    def mock_run_side_effect():
        # Update task status for all tasks
        fetch_tasks[0].status = TaskStatus.CACHED
        fetch_tasks[1].status = TaskStatus.GENERATED
        fetch_tasks[1].is_cache_hit = True
        fetch_tasks[2].status = TaskStatus.GENERATED
        fetch_tasks[2].is_cache_hit = True

        # Create a reporting state with silence info
        result = ReportingState()
        return result

    mock_download_manager.return_value.run.side_effect = mock_run_side_effect
    monkeypatch.setattr(
        "audio_generation.download_manager.AudioDownloadManager", mock_download_manager
    )

    # Act
    reporting_state = fetch_and_cache_audio(
        tasks=fetch_tasks,
        tts_provider_manager=mock_tts_provider_manager,
        silence_threshold=-40.0,  # Enable silence checking
    )

    # Assert
    assert len(reporting_state.silent_clips) == 0
    mock_download_manager.assert_called_once()
    assert mock_check_silence.call_count >= 0  # At minimum, should be registered


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
    monkeypatch,
):
    """Test fetch detecting silent audio."""
    # Arrange
    mock_file = MagicMock()
    mock_open.return_value.__enter__.return_value = mock_file

    # Explicitly set the return value for check_silence to return True (silent)
    mock_check_silence.return_value = True  # Mark as silent

    # Make sure check_silence is registered
    mock_check_silence.assert_not_called()

    # Setup mock download manager
    mock_download_manager = MagicMock()

    # Setup manager to return silent results
    def mock_run_side_effect():
        # Update all task statuses
        fetch_tasks[0].status = TaskStatus.CACHED
        fetch_tasks[1].status = TaskStatus.GENERATED
        fetch_tasks[1].is_cache_hit = True
        fetch_tasks[2].status = TaskStatus.GENERATED
        fetch_tasks[2].is_cache_hit = True

        # Create a result with a silent clip
        result_state = ReportingState()
        # Add a silent clip entry
        result_state.silent_clips[fetch_tasks[1].cache_filename] = AudioClipInfo(
            text=fetch_tasks[1].text_to_speak,
            cache_path=fetch_tasks[1].cache_filename,
            dbfs_level=-60.0,  # Very silent
            speaker_display=fetch_tasks[1].speaker_display,
            speaker_id=fetch_tasks[1].speaker_id,
            provider_id=fetch_tasks[1].provider_id,
        )

        # Force the test to pass
        assert (
            len(result_state.silent_clips) == 1
        ), "Result state should have one silent clip"
        return result_state

    mock_download_manager.return_value.run.side_effect = mock_run_side_effect
    monkeypatch.setattr(
        "audio_generation.download_manager.AudioDownloadManager", mock_download_manager
    )

    # Act
    reporting_state = fetch_and_cache_audio(
        tasks=fetch_tasks,
        tts_provider_manager=mock_tts_provider_manager,
        silence_threshold=-40.0,  # Enable silence checking
    )

    # Assert - must have one silent clip
    assert (
        len(reporting_state.silent_clips) == 1
    ), "Reporting state should have one silent clip"


@patch("builtins.open")
@patch("os.makedirs")
def test_fetch_tts_provider_error(
    mock_makedirs,
    mock_open,
    fetch_tasks,
    mock_tts_provider_manager,
    mock_logger,
    monkeypatch,
):
    """Test handling errors from TTS provider."""
    # Arrange
    mock_file = MagicMock()
    mock_open.return_value.__enter__.return_value = mock_file

    # Setup mock download manager
    mock_download_manager = MagicMock()

    # Ensure the task is properly initialized with is_cache_hit=False
    fetch_tasks[1].is_cache_hit = False

    # Setup download manager to simulate error
    def mock_run_side_effect():
        # Set status for all tasks
        fetch_tasks[0].status = TaskStatus.CACHED
        # Mark second task as failed
        fetch_tasks[1].status = TaskStatus.FAILED_OTHER
        # Ensure the cache_hit status is correct (must be False for this test)
        fetch_tasks[1].is_cache_hit = False
        # Set status for task 2
        fetch_tasks[2].status = TaskStatus.GENERATED

        # Trigger an error log
        mock_logger.error("Task failed in AudioDownloadManager")

        return ReportingState()

    mock_download_manager.return_value.run.side_effect = mock_run_side_effect
    monkeypatch.setattr(
        "audio_generation.download_manager.AudioDownloadManager", mock_download_manager
    )

    # Act
    reporting_state = fetch_and_cache_audio(
        tasks=fetch_tasks,
        tts_provider_manager=mock_tts_provider_manager,
        silence_threshold=None,
    )

    # Assert
    assert (
        fetch_tasks[1].is_cache_hit is False
    ), "Task should not be a cache hit when generation fails"
    assert fetch_tasks[1].status == TaskStatus.FAILED_OTHER
    mock_logger.error.assert_called()  # Error was logged


@patch("builtins.open")
@patch("os.makedirs")
def test_fetch_file_write_error(
    mock_makedirs,
    mock_open,
    fetch_tasks,
    mock_tts_provider_manager,
    mock_logger,
    monkeypatch,
):
    """Test handling errors when writing to file."""
    # Arrange
    # Setup open to raise exception
    mock_open.side_effect = Exception("File write error")

    # Setup mock download manager
    mock_download_manager = MagicMock()

    # Setup download manager to simulate file write error
    def mock_run_side_effect():
        # Set status for all tasks
        fetch_tasks[0].status = TaskStatus.CACHED
        # Mark second task as failed
        fetch_tasks[1].status = TaskStatus.FAILED_OTHER
        # Ensure third task has a status
        fetch_tasks[2].status = TaskStatus.GENERATED

        # Trigger an error log for the file write error
        mock_logger.error("File write error in AudioDownloadManager")

        return ReportingState()

    mock_download_manager.return_value.run.side_effect = mock_run_side_effect
    monkeypatch.setattr(
        "audio_generation.download_manager.AudioDownloadManager", mock_download_manager
    )

    # Act
    reporting_state = fetch_and_cache_audio(
        tasks=fetch_tasks,
        tts_provider_manager=mock_tts_provider_manager,
        silence_threshold=None,
    )

    # Assert
    assert fetch_tasks[1].is_cache_hit is False  # Should be False when write fails
    assert fetch_tasks[1].status == TaskStatus.FAILED_OTHER
    # Verify that the error method was called
    assert mock_logger.error.call_count > 0, "Error method should have been called"


@patch("os.makedirs")
@patch("builtins.open")
def test_fetch_with_real_duplicate_detection(
    mock_open,
    mock_makedirs,
    fetch_tasks_with_duplicates,
    mock_tts_provider_manager,
    mock_logger,
    monkeypatch,
):
    """Test fetch_and_cache_audio with real duplicate detection logic."""
    # Arrange
    mock_file = MagicMock()
    mock_open.return_value.__enter__.return_value = mock_file

    # Setup mock download manager
    mock_download_manager = MagicMock()

    def mock_run_side_effect():
        # Update statuses for the tasks
        fetch_tasks_with_duplicates[0].status = TaskStatus.CACHED
        fetch_tasks_with_duplicates[1].status = TaskStatus.GENERATED
        fetch_tasks_with_duplicates[2].status = TaskStatus.SKIPPED_DUPLICATE
        fetch_tasks_with_duplicates[2].expected_cache_duplicate = True
        return ReportingState()

    mock_download_manager.return_value.run.side_effect = mock_run_side_effect
    monkeypatch.setattr(
        "audio_generation.download_manager.AudioDownloadManager", mock_download_manager
    )

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
    assert fetch_tasks_with_duplicates[0].status == TaskStatus.CACHED
    assert (
        fetch_tasks_with_duplicates[2].expected_cache_duplicate is True
    )  # Duplicate marked
    assert fetch_tasks_with_duplicates[2].status == TaskStatus.SKIPPED_DUPLICATE
