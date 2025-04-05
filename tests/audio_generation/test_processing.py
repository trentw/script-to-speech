"""
Unit tests for the audio_generation.processing module.

This module tests the core processing functions for audio generation, including
planning audio generation tasks, applying cache overrides, and checking for silent
audio clips.
"""

import os
from unittest.mock import MagicMock, patch

import pytest

from audio_generation.models import AudioClipInfo, AudioGenerationTask, ReportingState
from audio_generation.processing import (
    apply_cache_overrides,
    check_audio_silence,
    check_for_silence,
    determine_speaker,
    generate_chunk_hash,
    plan_audio_generation,
)


@pytest.fixture
def sample_dialogues():
    """Fixture providing sample dialogue chunks for testing."""
    return [
        {
            "type": "dialog",
            "speaker": "JOHN",
            "text": "Hello world.",
            "raw_text": "Hello world.",
        },
        {
            "type": "action",
            "speaker": None,
            "text": "John walks away.",
            "raw_text": "John walks away.",
        },
        {
            "type": "dialog",
            "speaker": "MARY",
            "text": "Goodbye!",
            "raw_text": "Goodbye!",
        },
    ]


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
def mock_text_processor_manager():
    """Fixture providing a mock TextProcessorManager."""
    mock = MagicMock()

    # Setup mock methods
    def mock_process_chunk(chunk):
        # Simple mock that just returns the input chunk with slight modification
        processed = chunk.copy()
        if processed.get("text"):
            processed["text"] = processed["text"] + "!"  # Add exclamation for testing
        return processed, []

    mock.process_chunk.side_effect = mock_process_chunk

    # Mock preprocess_chunks to return the input chunks unchanged
    mock.preprocess_chunks.side_effect = lambda chunks: chunks

    return mock


@pytest.fixture
def mock_logger():
    """Fixture providing a mock logger."""
    with patch("audio_generation.processing.logger") as mock:
        yield mock


class TestGenerateChunkHash:
    """Tests for generate_chunk_hash function."""

    def test_hash_with_text_and_speaker(self):
        """Test generating hash with text and speaker specified."""
        # Arrange
        text = "Hello world"
        speaker = "JOHN"

        # Act
        hash1 = generate_chunk_hash(text, speaker)
        hash2 = generate_chunk_hash(text, speaker)  # Same inputs
        hash3 = generate_chunk_hash(text, "MARY")  # Different speaker
        hash4 = generate_chunk_hash("Different text", speaker)  # Different text

        # Assert
        assert len(hash1) == 32
        assert all(c in "0123456789abcdef" for c in hash1)
        assert hash1 == hash2  # Same inputs produce same hash
        assert hash1 != hash3  # Different speaker produces different hash
        assert hash1 != hash4  # Different text produces different hash

    def test_hash_with_none_speaker(self):
        """Test generating hash with None speaker."""
        # Arrange
        text = "Hello world"

        # Act
        hash1 = generate_chunk_hash(text, None)
        hash2 = generate_chunk_hash(
            text, ""
        )  # Empty string should be equivalent to None

        # Assert
        assert len(hash1) == 32
        assert hash1 == hash2  # None and empty string should produce same hash


class TestDetermineSpeaker:
    """Tests for determine_speaker function."""

    def test_determine_valid_speaker(self):
        """Test determining speaker with valid speaker in dialogue."""
        # Arrange
        dialogue = {"speaker": "JOHN", "text": "Hello world"}

        # Act
        result = determine_speaker(dialogue)

        # Assert
        assert result == "JOHN"

    def test_determine_none_speaker(self):
        """Test determining speaker with None speaker in dialogue."""
        # Arrange
        dialogue = {"speaker": None, "text": "Action description"}

        # Act
        result = determine_speaker(dialogue)

        # Assert
        assert result is None

    def test_determine_empty_speaker(self):
        """Test determining speaker with empty string speaker in dialogue."""
        # Arrange
        dialogue = {"speaker": "", "text": "Action description"}

        # Act
        result = determine_speaker(dialogue)

        # Assert
        assert result is None

    def test_determine_none_string_speaker(self):
        """Test determining speaker with 'none' string in dialogue."""
        # Arrange
        dialogue1 = {"speaker": "none", "text": "Action description"}
        dialogue2 = {
            "speaker": "NoNe",
            "text": "Action description",
        }  # Case insensitive

        # Act
        result1 = determine_speaker(dialogue1)
        result2 = determine_speaker(dialogue2)

        # Assert
        assert result1 is None
        assert result2 is None

    def test_determine_missing_speaker(self):
        """Test determining speaker when speaker key is missing."""
        # Arrange
        dialogue = {"text": "Action description"}

        # Act
        result = determine_speaker(dialogue)

        # Assert
        assert result is None


class TestPlanAudioGeneration:
    """Tests for plan_audio_generation function."""

    def test_plan_with_empty_dialogues(
        self, mock_tts_provider_manager, mock_text_processor_manager, mock_logger
    ):
        """Test planning with empty dialogues list."""
        # Arrange
        dialogues = []

        # Act
        tasks, reporting_state = plan_audio_generation(
            dialogues=dialogues,
            tts_provider_manager=mock_tts_provider_manager,
            processor=mock_text_processor_manager,
            cache_folder="/tmp/cache",
            cache_overrides_dir=None,
        )

        # Assert
        assert len(tasks) == 0
        assert len(reporting_state.cache_misses) == 0
        assert len(reporting_state.silent_clips) == 0

    @patch("os.listdir")
    def test_plan_with_existing_cache(
        self,
        mock_listdir,
        sample_dialogues,
        mock_tts_provider_manager,
        mock_text_processor_manager,
        mock_logger,
    ):
        """Test planning with existing cache files."""
        # Arrange
        mock_listdir.return_value = [
            "cached_hash1~~cached_hash2~~elevenlabs~~voice_id_123.mp3"
        ]

        # Act
        with patch("audio_generation.processing.generate_chunk_hash") as mock_hash:
            # Return predictable hashes
            mock_hash.side_effect = [
                "cached_hash1",
                "cached_hash2",
                "hash3",
                "hash4",
                "hash5",
                "hash6",
            ]

            tasks, reporting_state = plan_audio_generation(
                dialogues=sample_dialogues,
                tts_provider_manager=mock_tts_provider_manager,
                processor=mock_text_processor_manager,
                cache_folder="/tmp/cache",
                cache_overrides_dir=None,
            )

        # Assert
        assert len(tasks) == 3

        # First task is a cache hit
        assert tasks[0].is_cache_hit is True
        assert (
            tasks[0].cache_filename
            == "cached_hash1~~cached_hash2~~elevenlabs~~voice_id_123.mp3"
        )

        # Other tasks are cache misses
        assert tasks[1].is_cache_hit is False
        assert tasks[2].is_cache_hit is False

        # Reporting state includes misses
        assert len(reporting_state.cache_misses) == 2
        assert tasks[1].cache_filename in reporting_state.cache_misses
        assert tasks[2].cache_filename in reporting_state.cache_misses

    def test_plan_with_expected_silence(
        self,
        sample_dialogues,
        mock_tts_provider_manager,
        mock_text_processor_manager,
        mock_logger,
    ):
        """Test planning with a dialogue that should be silent."""
        # Arrange
        # Create silent dialogue
        silent_dialogue = sample_dialogues[1].copy()
        silent_dialogue["text"] = ""
        modified_dialogues = [sample_dialogues[0], silent_dialogue, sample_dialogues[2]]

        modified_processor = MagicMock()
        modified_processor.preprocess_chunks.return_value = modified_dialogues
        modified_processor.process_chunk.side_effect = lambda chunk: (chunk, [])

        # Act
        tasks, reporting_state = plan_audio_generation(
            dialogues=modified_dialogues,
            tts_provider_manager=mock_tts_provider_manager,
            processor=modified_processor,
            cache_folder="/tmp/cache",
            cache_overrides_dir=None,
        )

        # Assert
        assert tasks[1].expected_silence is True  # Silent task is marked
        assert tasks[0].expected_silence is False  # Non-silent tasks are not marked
        assert tasks[2].expected_silence is False

    @patch("os.path.exists")
    def test_plan_with_cache_overrides(
        self,
        mock_exists,
        sample_dialogues,
        mock_tts_provider_manager,
        mock_text_processor_manager,
        mock_logger,
    ):
        """Test planning with cache override files available."""
        # Arrange
        mock_exists.side_effect = (
            lambda path: "voice_id_123" in path
        )  # Override available for JOHN

        # Act
        tasks, reporting_state = plan_audio_generation(
            dialogues=sample_dialogues,
            tts_provider_manager=mock_tts_provider_manager,
            processor=mock_text_processor_manager,
            cache_folder="/tmp/cache",
            cache_overrides_dir="/tmp/overrides",
        )

        # Assert
        assert tasks[0].is_override_available is True  # John's task has override
        assert tasks[1].is_override_available is False  # Other tasks don't
        assert tasks[2].is_override_available is False

    def test_plan_handles_processor_exception(
        self, sample_dialogues, mock_tts_provider_manager, mock_logger
    ):
        """Test error handling when processor raises an exception."""
        # Arrange
        failing_processor = MagicMock()
        failing_processor.preprocess_chunks.side_effect = Exception(
            "Preprocessing failed"
        )

        # Act and Assert
        with pytest.raises(Exception, match="Preprocessing failed"):
            plan_audio_generation(
                dialogues=sample_dialogues,
                tts_provider_manager=mock_tts_provider_manager,
                processor=failing_processor,
                cache_folder="/tmp/cache",
                cache_overrides_dir=None,
            )

        mock_logger.error.assert_called()

    @patch("os.listdir")
    def test_plan_with_missing_cache_folder(
        self,
        mock_listdir,
        sample_dialogues,
        mock_tts_provider_manager,
        mock_text_processor_manager,
        mock_logger,
    ):
        """Test planning when cache folder doesn't exist."""
        # Arrange
        mock_listdir.side_effect = FileNotFoundError("Cache folder not found")

        # Act
        tasks, reporting_state = plan_audio_generation(
            dialogues=sample_dialogues,
            tts_provider_manager=mock_tts_provider_manager,
            processor=mock_text_processor_manager,
            cache_folder="/tmp/missing_cache",
            cache_overrides_dir=None,
        )

        # Assert
        assert len(tasks) == 3
        # All tasks should be cache misses
        for task in tasks:
            assert task.is_cache_hit is False

        # Warning should be logged
        mock_logger.warning.assert_called_with(
            "Cache folder not found: /tmp/missing_cache. Assuming empty cache."
        )


class TestApplyCacheOverrides:
    """Tests for apply_cache_overrides function."""

    @pytest.fixture
    def sample_tasks(self):
        """Fixture providing sample tasks for testing."""
        return [
            AudioGenerationTask(
                idx=0,
                original_dialogue={
                    "type": "dialog",
                    "speaker": "JOHN",
                    "text": "Hello",
                },
                processed_dialogue={
                    "type": "dialog",
                    "speaker": "JOHN",
                    "text": "Hello!",
                },
                text_to_speak="Hello!",
                speaker="JOHN",
                provider_id="elevenlabs",
                speaker_id="voice_id_123",
                speaker_display="JOHN",
                cache_filename="hash1~~hash2~~elevenlabs~~voice_id_123.mp3",
                cache_filepath="/path/to/cache/hash1~~hash2~~elevenlabs~~voice_id_123.mp3",
                is_cache_hit=False,
                is_override_available=True,  # Has an override available
            ),
            AudioGenerationTask(
                idx=1,
                original_dialogue={
                    "type": "dialog",
                    "speaker": "MARY",
                    "text": "Goodbye",
                },
                processed_dialogue={
                    "type": "dialog",
                    "speaker": "MARY",
                    "text": "Goodbye!",
                },
                text_to_speak="Goodbye!",
                speaker="MARY",
                provider_id="openai",
                speaker_id="voice_id_456",
                speaker_display="MARY",
                cache_filename="hash3~~hash4~~openai~~voice_id_456.mp3",
                cache_filepath="/path/to/cache/hash3~~hash4~~openai~~voice_id_456.mp3",
                is_cache_hit=False,
                is_override_available=False,  # No override available
            ),
        ]

    def test_apply_overrides_when_available(self, sample_tasks, mock_logger):
        """Test applying cache overrides when they are available."""
        # Arrange
        with patch("os.makedirs") as mock_makedirs, patch("os.replace") as mock_replace:

            # Act
            apply_cache_overrides(
                tasks=sample_tasks,
                cache_overrides_dir="/path/to/overrides",
                cache_folder="/path/to/cache",
            )

            # Assert
            mock_replace.assert_called_once_with(
                "/path/to/overrides/hash1~~hash2~~elevenlabs~~voice_id_123.mp3",
                "/path/to/cache/hash1~~hash2~~elevenlabs~~voice_id_123.mp3",
            )

            assert (
                sample_tasks[0].is_cache_hit is True
            )  # Task with override is now a cache hit
            assert (
                sample_tasks[1].is_cache_hit is False
            )  # Task without override remains unchanged

    def test_no_overrides_dir_provided(self, sample_tasks, mock_logger):
        """Test behavior when no overrides directory is provided."""
        # Arrange - tasks already setup in fixture

        # Act
        apply_cache_overrides(
            tasks=sample_tasks,
            cache_overrides_dir=None,
            cache_folder="/path/to/cache",
        )

        # Assert
        assert sample_tasks[0].is_cache_hit is False  # Task status unchanged
        assert sample_tasks[1].is_cache_hit is False

        mock_logger.info.assert_called_with(
            "Cache overrides directory not specified, skipping override application."
        )

    def test_exception_during_override(self, sample_tasks, mock_logger):
        """Test handling of exceptions during override application."""
        # Arrange
        with patch("os.makedirs") as mock_makedirs, patch("os.replace") as mock_replace:

            # Setup replace to raise exception
            mock_replace.side_effect = Exception("File not found")

            # Act
            apply_cache_overrides(
                tasks=sample_tasks,
                cache_overrides_dir="/path/to/overrides",
                cache_folder="/path/to/cache",
            )

            # Assert
            assert (
                sample_tasks[0].is_cache_hit is False
            )  # Task status remains unchanged
            mock_logger.error.assert_called()


class TestCheckForSilence:
    """Tests for check_for_silence function."""

    @pytest.fixture
    def sample_silence_tasks(self):
        """Fixture providing sample tasks for silence checking."""
        return [
            # Cache hit that is expected to be silent
            AudioGenerationTask(
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
            ),
            # Cache hit that should be checked for silence
            AudioGenerationTask(
                idx=1,
                original_dialogue={
                    "type": "dialog",
                    "speaker": "JOHN",
                    "text": "Hello",
                },
                processed_dialogue={
                    "type": "dialog",
                    "speaker": "JOHN",
                    "text": "Hello!",
                },
                text_to_speak="Hello!",
                speaker="JOHN",
                provider_id="elevenlabs",
                speaker_id="voice_id_123",
                speaker_display="JOHN",
                cache_filename="hash1~~hash2~~elevenlabs~~voice_id_123.mp3",
                cache_filepath="/path/to/cache/hash1~~hash2~~elevenlabs~~voice_id_123.mp3",
                is_cache_hit=True,
                expected_silence=False,
            ),
            # Cache miss that doesn't need silence checking
            AudioGenerationTask(
                idx=2,
                original_dialogue={
                    "type": "dialog",
                    "speaker": "MARY",
                    "text": "Goodbye",
                },
                processed_dialogue={
                    "type": "dialog",
                    "speaker": "MARY",
                    "text": "Goodbye!",
                },
                text_to_speak="Goodbye!",
                speaker="MARY",
                provider_id="openai",
                speaker_id="voice_id_456",
                speaker_display="MARY",
                cache_filename="hash3~~hash4~~openai~~voice_id_456.mp3",
                cache_filepath="/path/to/cache/hash3~~hash4~~openai~~voice_id_456.mp3",
                is_cache_hit=False,
                expected_silence=False,
            ),
        ]

    def test_silence_checking_disabled(self, sample_silence_tasks, mock_logger):
        """Test behavior when silence checking is disabled."""
        # Arrange - tasks already setup in fixture

        # Act
        reporting_state = check_for_silence(
            tasks=sample_silence_tasks,
            silence_threshold=None,
        )

        # Assert
        assert len(reporting_state.silent_clips) == 0
        assert sample_silence_tasks[1].is_cache_hit is True  # Still a hit

        mock_logger.info.assert_called_with("Silence checking disabled. Skipping.")

    @patch("audio_generation.processing.check_audio_silence")
    @patch("builtins.open")
    def test_check_silent_clip(
        self, mock_open, mock_check_silence, sample_silence_tasks, mock_logger
    ):
        """Test silence checking on a clip that is silent."""
        # Arrange
        mock_file = MagicMock()
        mock_file.__enter__.return_value.read.return_value = b"audio_data"
        mock_open.return_value = mock_file

        # Setup mock to actually update the reporting state
        def mock_check_silence_fn(
            task, audio_data, silence_threshold, reporting_state, log_prefix
        ):
            # Add a silent clip to the reporting state
            reporting_state.silent_clips[task.cache_filename] = AudioClipInfo(
                text=task.text_to_speak,
                cache_path=task.cache_filename,
                dbfs_level=-60.0,
                speaker_display=task.speaker_display,
                speaker_id=task.speaker_id,
                provider_id=task.provider_id,
            )
            return True  # Signal that it's silent

        mock_check_silence.side_effect = mock_check_silence_fn

        # Act
        reporting_state = check_for_silence(
            tasks=sample_silence_tasks,
            silence_threshold=-40.0,
        )

        # Assert
        assert (
            sample_silence_tasks[1].is_cache_hit is False
        )  # Now marked as a miss because it's silent
        assert len(reporting_state.silent_clips) == 1
        assert sample_silence_tasks[1].cache_filename in reporting_state.silent_clips
        assert (
            mock_check_silence.call_count == 1
        )  # Only one task should be checked (non-silent cache hit)

    @patch("audio_generation.processing.check_audio_silence")
    @patch("builtins.open")
    def test_check_non_silent_clip(
        self, mock_open, mock_check_silence, sample_silence_tasks, mock_logger
    ):
        """Test silence checking on a clip that is not silent."""
        # Arrange
        mock_file = MagicMock()
        mock_file.__enter__.return_value.read.return_value = b"audio_data"
        mock_open.return_value = mock_file

        # Setup mock to indicate clip is not silent
        mock_check_silence.return_value = False

        # Act
        reporting_state = check_for_silence(
            tasks=sample_silence_tasks,
            silence_threshold=-40.0,
        )

        # Assert
        assert sample_silence_tasks[1].is_cache_hit is True  # Still a hit
        assert len(reporting_state.silent_clips) == 0

    @patch("builtins.open")
    def test_file_read_error(self, mock_open, sample_silence_tasks, mock_logger):
        """Test handling of file read errors during silence checking."""
        # Arrange
        mock_open.side_effect = Exception("File read error")

        # Act
        reporting_state = check_for_silence(
            tasks=sample_silence_tasks,
            silence_threshold=-40.0,
        )

        # Assert
        assert sample_silence_tasks[1].is_cache_hit is True  # Status unchanged
        assert len(reporting_state.silent_clips) == 0
        mock_logger.error.assert_called()

    def test_only_checks_cache_hits(self, sample_silence_tasks, mock_logger):
        """Test that only cache hits are checked for silence."""
        # Arrange
        captured_tasks = []

        # Define a side effect that captures which task was passed
        def capture_task_side_effect(
            task, audio_data, silence_threshold, reporting_state, log_prefix
        ):
            captured_tasks.append(task)
            return False  # Not silent

        # Act
        with patch("builtins.open") as mock_open, patch(
            "audio_generation.processing.check_audio_silence"
        ) as mock_check_silence:
            # Setup our side effect
            mock_check_silence.side_effect = capture_task_side_effect

            # Setup open to return some audio data
            mock_file = MagicMock()
            mock_file.__enter__.return_value.read.return_value = b"audio_data"
            mock_open.return_value = mock_file

            check_for_silence(
                tasks=sample_silence_tasks,
                silence_threshold=-40.0,
            )

        # Assert
        # Verify exactly one task was checked
        assert len(captured_tasks) == 1

        # Verify it was the right task (index 1 - the non-silent cache hit)
        assert captured_tasks[0] is sample_silence_tasks[1]

        # Verify open was called for the right file
        mock_open.assert_called_once_with(sample_silence_tasks[1].cache_filepath, "rb")


class TestCheckAudioSilence:
    """Tests for check_audio_silence function."""

    @pytest.fixture
    def silence_task(self):
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
    def expected_silence_task(self):
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

    @patch("audio_generation.processing.check_audio_level")
    def test_silent_clip(self, mock_check_level, silence_task, mock_logger):
        """Test checking a clip that is silent."""
        # Arrange
        mock_check_level.return_value = -60.0  # Very low level
        reporting_state = ReportingState()

        # Act
        result = check_audio_silence(
            task=silence_task,
            audio_data=b"audio_data",
            silence_threshold=-40.0,
            reporting_state=reporting_state,
            log_prefix="",
        )

        # Assert
        assert result is True  # Indicates silence
        assert silence_task.checked_silence_level == -60.0
        assert len(reporting_state.silent_clips) == 1
        assert silence_task.cache_filename in reporting_state.silent_clips

    @patch("audio_generation.processing.check_audio_level")
    def test_non_silent_clip(self, mock_check_level, silence_task, mock_logger):
        """Test checking a clip that is not silent."""
        # Arrange
        mock_check_level.return_value = -20.0  # Higher level
        reporting_state = ReportingState()

        # Act
        result = check_audio_silence(
            task=silence_task,
            audio_data=b"audio_data",
            silence_threshold=-40.0,
            reporting_state=reporting_state,
            log_prefix="",
        )

        # Assert
        assert result is False  # Not silent
        assert silence_task.checked_silence_level == -20.0
        assert len(reporting_state.silent_clips) == 0

    @patch("audio_generation.processing.check_audio_level")
    def test_expected_silence_skipped(
        self, mock_check_level, expected_silence_task, mock_logger
    ):
        """Test that expected silence tasks are skipped."""
        # Arrange
        reporting_state = ReportingState()

        # Act
        result = check_audio_silence(
            task=expected_silence_task,
            audio_data=b"audio_data",
            silence_threshold=-40.0,
            reporting_state=reporting_state,
            log_prefix="",
        )

        # Assert
        assert result is False  # Not marked as silent (skipped check)
        mock_check_level.assert_not_called()
        assert len(reporting_state.silent_clips) == 0

    @patch("audio_generation.processing.check_audio_level")
    @patch("audio_generation.processing.truncate_text")
    def test_with_log_prefix(
        self, mock_truncate, mock_check_level, silence_task, mock_logger
    ):
        """Test logging with a prefix."""
        # Arrange
        mock_check_level.return_value = -60.0
        mock_truncate.return_value = "Hello..."
        reporting_state = ReportingState()

        # Act
        check_audio_silence(
            task=silence_task,
            audio_data=b"audio_data",
            silence_threshold=-40.0,
            reporting_state=reporting_state,
            log_prefix="PREFIX: ",
        )

        # Assert
        # Check that at least one warning log message uses the prefix
        prefix_used = False
        for call in mock_logger.warning.call_args_list:
            args, kwargs = call
            if args and isinstance(args[0], str) and args[0].startswith("PREFIX:"):
                prefix_used = True
                break

        assert prefix_used, "Log prefix not used in any warning messages"

    @patch("audio_generation.processing.check_audio_level")
    def test_none_level_handled(self, mock_check_level, silence_task, mock_logger):
        """Test handling of None returned from check_audio_level."""
        # Arrange
        mock_check_level.return_value = None
        reporting_state = ReportingState()

        # Act
        result = check_audio_silence(
            task=silence_task,
            audio_data=b"audio_data",
            silence_threshold=-40.0,
            reporting_state=reporting_state,
            log_prefix="",
        )

        # Assert
        assert result is False  # Not silent (can't determine)
        assert len(reporting_state.silent_clips) == 0
