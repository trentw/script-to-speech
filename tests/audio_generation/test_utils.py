"""
Unit tests for the audio_generation.utils module.

This module tests utility functions for audio generation, including
audio level checking, concatenation, file loading, and text truncation.
"""

import io
import json
from datetime import datetime
from unittest.mock import ANY, MagicMock, call, mock_open, patch

import pytest
from pydub import AudioSegment

from script_to_speech.audio_generation.utils import (
    check_audio_level,
    concatenate_tasks_batched,
    load_json_chunks,
    truncate_text,
)


class TestAudioLevelChecking:
    """Tests for audio level checking function."""

    def test_check_audio_level_with_valid_audio(self):
        """Test checking audio level with valid audio data."""
        # Arrange
        with patch(
            "script_to_speech.audio_generation.utils.AudioSegment"
        ) as mock_audio_segment:
            # Set up mock to return our audio with a known dBFS value
            mock_segment = MagicMock()
            mock_segment.max_dBFS = -60.0
            mock_audio_segment.from_mp3.return_value = mock_segment
            audio_bytes = b"mock_audio_data"

            # Act
            result = check_audio_level(audio_bytes)

            # Assert
            assert result == -60.0
            mock_audio_segment.from_mp3.assert_called_once()

    def test_check_audio_level_with_empty_data(self):
        """Test checking audio level with empty data."""
        # Arrange
        audio_bytes = b""

        # Act
        result = check_audio_level(audio_bytes)

        # Assert
        assert result is None

    def test_check_audio_level_with_invalid_audio(self):
        """Test checking audio level with invalid audio data."""
        # Arrange
        with patch(
            "script_to_speech.audio_generation.utils.AudioSegment"
        ) as mock_audio_segment:
            mock_audio_segment.from_mp3.side_effect = Exception("Invalid audio")
            audio_bytes = b"invalid_audio_data"

            # Act
            result = check_audio_level(audio_bytes)

            # Assert
            assert result is None


class TestConcatenateTasksBatched:
    """Tests for the batched audio concatenation function."""

    @pytest.fixture
    def mock_logger(self):
        """Fixture providing a mock logger."""
        with patch("script_to_speech.audio_generation.utils.logger") as mock:
            yield mock

    @pytest.fixture
    def mock_audio_generation_task(self):
        """Helper to create a mock AudioGenerationTask with a cache_filepath."""

        def _make(idx, cache_filepath, expected_silence=False):
            task = MagicMock()
            task.cache_filepath = cache_filepath
            task.idx = idx
            task.expected_silence = expected_silence
            return task

        return _make

    def test_concatenate_single_task(self, mock_logger, mock_audio_generation_task):
        """Test concatenating a single audio task."""
        # Arrange
        output_path = "/path/to/output.mp3"
        cache_path = "/tmp/audio1.mp3"
        task = mock_audio_generation_task(1, cache_path)
        mock_segment = MagicMock(spec=AudioSegment)
        mock_segment.__len__.return_value = 1000

        with (
            patch(
                "script_to_speech.audio_generation.utils.AudioSegment"
            ) as mock_audio_segment,
            patch("os.path.exists") as mock_exists,
            patch("os.makedirs") as mock_makedirs,
            patch("os.listdir") as mock_listdir,
            patch("os.remove") as mock_remove,
            patch("os.rmdir") as mock_rmdir,
            patch("os.path.getsize") as mock_getsize,
        ):

            # Track all empty() mocks
            empty_mocks = []
            created_batch_files = set()

            def empty_side_effect():
                m = MagicMock()
                empty_mocks.append(m)
                # Simulate accumulation of audio data
                m._length = 0

                def iadd_side_effect(other):
                    m._length += 1000  # Simulate adding a segment of 1000ms
                    return m

                m.__iadd__.side_effect = iadd_side_effect
                m.__len__.side_effect = lambda: m._length if m._length > 0 else 1000

                # Patch export to record batch file creation
                def export_side_effect(path, format=None):
                    created_batch_files.add(path)

                m.export.side_effect = export_side_effect
                return m

            mock_audio_segment.empty.side_effect = empty_side_effect

            # Track all from_mp3 calls (for both cache and batch files)
            from_mp3_mocks = []

            def from_mp3_side_effect(path):
                m = MagicMock()
                m.__len__.return_value = 1000
                m.export = MagicMock()
                from_mp3_mocks.append((path, m))
                return m

            mock_audio_segment.from_mp3.side_effect = from_mp3_side_effect

            # Simulate temp_batches directory and batch file
            temp_batches_dir = "/path/to/temp_batches"
            batch_file = "/path/to/temp_batches/batch_0.mp3"

            def exists_side_effect(path):
                return (
                    path == cache_path
                    or path == temp_batches_dir
                    or path in created_batch_files
                )

            mock_exists.side_effect = exists_side_effect
            mock_listdir.side_effect = lambda path: (
                ["batch_0.mp3"] if path == temp_batches_dir else []
            )

            # Patch getsize to avoid FileNotFoundError
            mock_getsize.side_effect = lambda path: (
                1234 if path == output_path else 5678
            )

            # Act
            concatenate_tasks_batched(
                [task], output_path, batch_size=1, gap_duration_ms=0
            )

            # Assert
            # Should call from_mp3 for the cache file and for the batch file (if batch file was created)
            assert any(call[0] == cache_path for call in from_mp3_mocks)
            if batch_file in created_batch_files:
                assert any(call[0] == batch_file for call in from_mp3_mocks)
            # The export should be called on the last empty() mock (final_audio)
            assert empty_mocks, "No AudioSegment.empty() calls captured"
            empty_mocks[-1].export.assert_called_once_with(output_path, format="mp3")
            mock_makedirs.assert_called()
            mock_rmdir.assert_called()

    def test_concatenate_multiple_tasks_with_gap_and_batch(
        self, mock_logger, mock_audio_generation_task
    ):
        """Test concatenating multiple audio tasks with a gap and batching."""
        output_path = "/path/to/output.mp3"
        cache_paths = [f"/tmp/audio{i}.mp3" for i in range(3)]
        tasks = [mock_audio_generation_task(i, cache_paths[i]) for i in range(3)]
        mock_segments = [MagicMock(spec=AudioSegment) for _ in range(3)]
        for seg in mock_segments:
            seg.__len__.return_value = 1000
            seg.export = MagicMock()

        # Patch AudioSegment and os functions
        with (
            patch(
                "script_to_speech.audio_generation.utils.AudioSegment"
            ) as mock_audio_segment,
            patch("os.path.exists") as mock_exists,
            patch("os.makedirs") as mock_makedirs,
            patch("os.listdir") as mock_listdir,
            patch("os.remove") as mock_remove,
            patch("os.rmdir") as mock_rmdir,
            patch("os.path.getsize") as mock_getsize,
        ):

            # Track all empty() mocks
            empty_mocks = []
            created_batch_files = set()

            def empty_side_effect():
                m = MagicMock()
                empty_mocks.append(m)
                m._length = 0

                def iadd_side_effect(other):
                    m._length += 1000
                    return m

                m.__iadd__.side_effect = iadd_side_effect
                m.__len__.side_effect = lambda: m._length if m._length > 0 else 1000

                def export_side_effect(path, format=None):
                    created_batch_files.add(path)

                m.export.side_effect = export_side_effect
                return m

            mock_audio_segment.empty.side_effect = empty_side_effect
            mock_audio_segment.silent.return_value = MagicMock()

            # Track all from_mp3 calls (for both cache and batch files)
            from_mp3_mocks = []

            def from_mp3_side_effect(path):
                m = MagicMock()
                m.__len__.return_value = 1000
                m.export = MagicMock()
                from_mp3_mocks.append((path, m))
                return m

            mock_audio_segment.from_mp3.side_effect = from_mp3_side_effect

            # Simulate temp_batches directory and batch files
            temp_batches_dir = "/path/to/temp_batches"
            batch_files = [f"/path/to/temp_batches/batch_{i}.mp3" for i in range(2)]

            def exists_side_effect(path):
                return (
                    path in cache_paths
                    or path == temp_batches_dir
                    or path in created_batch_files
                )

            mock_exists.side_effect = exists_side_effect
            mock_listdir.side_effect = lambda path: (
                [f"batch_{i}.mp3" for i in range(2)] if path == temp_batches_dir else []
            )

            # Patch getsize to avoid FileNotFoundError
            mock_getsize.side_effect = lambda path: (
                1234 if path == output_path else 5678
            )

            # Act
            concatenate_tasks_batched(
                tasks, output_path, batch_size=2, gap_duration_ms=200
            )

            # Assert
            # Should call from_mp3 for each cache file and for each batch file
            for cp in cache_paths:
                assert any(call[0] == cp for call in from_mp3_mocks)
            for bf in batch_files:
                if bf in created_batch_files:
                    assert any(call[0] == bf for call in from_mp3_mocks)
            # The export should be called on the last empty() mock (final_audio)
            assert empty_mocks, "No AudioSegment.empty() calls captured"
            empty_mocks[-1].export.assert_called_once_with(output_path, format="mp3")
            mock_makedirs.assert_called()
            mock_audio_segment.silent.assert_called_with(duration=200)
            mock_rmdir.assert_called()

    def test_skips_tasks_with_missing_cache(
        self, mock_logger, mock_audio_generation_task
    ):
        """Test that tasks with missing cache files are skipped."""
        output_path = "/path/to/output.mp3"
        cache_path_valid = "/tmp/audio_valid.mp3"
        cache_path_missing = "/tmp/audio_missing.mp3"
        task_valid = mock_audio_generation_task(1, cache_path_valid)
        task_missing = mock_audio_generation_task(2, cache_path_missing)
        mock_segment = MagicMock(spec=AudioSegment)
        mock_segment.__len__.return_value = 1000
        mock_segment.export = MagicMock()

        with (
            patch(
                "script_to_speech.audio_generation.utils.AudioSegment"
            ) as mock_audio_segment,
            patch("os.path.exists") as mock_exists,
            patch("os.makedirs") as mock_makedirs,
            patch("os.listdir") as mock_listdir,
            patch("os.remove") as mock_remove,
            patch("os.rmdir") as mock_rmdir,
            patch("os.path.getsize") as mock_getsize,
        ):

            # Track all empty() mocks
            empty_mocks = []
            created_batch_files = set()

            def empty_side_effect():
                m = MagicMock()
                empty_mocks.append(m)
                m._length = 0

                def iadd_side_effect(other):
                    m._length += 1000
                    return m

                m.__iadd__.side_effect = iadd_side_effect
                m.__len__.side_effect = lambda: m._length if m._length > 0 else 1000

                def export_side_effect(path, format=None):
                    created_batch_files.add(path)

                m.export.side_effect = export_side_effect
                return m

            mock_audio_segment.empty.side_effect = empty_side_effect

            # Track all from_mp3 calls (for both cache and batch files)
            from_mp3_mocks = []

            def from_mp3_side_effect(path):
                m = MagicMock()
                m.__len__.return_value = 1000
                m.export = MagicMock()
                from_mp3_mocks.append((path, m))
                return m

            mock_audio_segment.from_mp3.side_effect = from_mp3_side_effect

            # Simulate temp_batches directory and batch file
            temp_batches_dir = "/path/to/temp_batches"
            batch_file = "/path/to/temp_batches/batch_0.mp3"

            def exists_side_effect(path):
                return (
                    path == cache_path_valid
                    or path == temp_batches_dir
                    or path in created_batch_files
                )

            mock_exists.side_effect = exists_side_effect
            mock_listdir.side_effect = lambda path: (
                ["batch_0.mp3"] if path == temp_batches_dir else []
            )

            # Patch getsize to avoid FileNotFoundError
            mock_getsize.side_effect = lambda path: (
                1234 if path == output_path else 5678
            )

            # Act
            concatenate_tasks_batched(
                [task_valid, task_missing], output_path, batch_size=1, gap_duration_ms=0
            )

            # Assert
            assert any(call[0] == cache_path_valid for call in from_mp3_mocks)
            if batch_file in created_batch_files:
                assert any(call[0] == batch_file for call in from_mp3_mocks)
            # The export should be called on the last empty() mock (final_audio)
            assert empty_mocks, "No AudioSegment.empty() calls captured"
            empty_mocks[-1].export.assert_called_once_with(output_path, format="mp3")
            mock_makedirs.assert_called()
            mock_rmdir.assert_called()

    def test_handles_no_valid_tasks(self, mock_logger, mock_audio_generation_task):
        """Test that no output is produced if all tasks are missing cache files."""
        output_path = "/path/to/output.mp3"
        cache_path_missing = "/tmp/audio_missing.mp3"
        task_missing = mock_audio_generation_task(1, cache_path_missing)

        with (
            patch(
                "script_to_speech.audio_generation.utils.AudioSegment"
            ) as mock_audio_segment,
            patch("os.path.exists") as mock_exists,
            patch("os.makedirs") as mock_makedirs,
            patch("os.listdir") as mock_listdir,
            patch("os.remove") as mock_remove,
            patch("os.rmdir") as mock_rmdir,
        ):

            mock_audio_segment.empty.return_value = MagicMock()
            mock_exists.return_value = False
            mock_listdir.return_value = []

            # Act
            concatenate_tasks_batched(
                [task_missing], output_path, batch_size=1, gap_duration_ms=0
            )

            # Assert
            mock_audio_segment.from_mp3.assert_not_called()
            mock_makedirs.assert_not_called()
            mock_rmdir.assert_not_called()


class TestLoadJsonChunks:
    """Tests for JSON chunks loading function."""

    def test_load_valid_json(self):
        """Test loading valid JSON chunks from a file."""
        # Arrange
        json_data = [
            {"type": "dialogue", "text": "Hello"},
            {"type": "action", "text": "John walks"},
        ]
        json_str = json.dumps(json_data)

        with patch("builtins.open", mock_open(read_data=json_str)) as mock_file:
            # Act
            result = load_json_chunks("test_file.json")

            # Assert
            mock_file.assert_called_once_with("test_file.json", "r", encoding="utf-8")
            assert len(result) == 2
            assert result[0]["type"] == "dialogue"
            assert result[0]["text"] == "Hello"
            assert result[1]["type"] == "action"
            assert result[1]["text"] == "John walks"

    def test_load_invalid_json(self):
        """Test loading invalid JSON from a file."""
        # Arrange
        invalid_json = "This is not valid JSON"

        with patch("builtins.open", mock_open(read_data=invalid_json)) as mock_file:
            # Act and Assert
            with pytest.raises(ValueError):
                load_json_chunks("test_file.json")

            mock_file.assert_called_once_with("test_file.json", "r", encoding="utf-8")

    def test_file_not_found(self):
        """Test handling of non-existent file."""
        # Arrange
        with patch("builtins.open", side_effect=FileNotFoundError()):
            # Act and Assert
            with pytest.raises(FileNotFoundError):
                load_json_chunks("non_existent_file.json")


class TestTruncateText:
    """Tests for text truncation function."""

    def test_truncate_short_text(self):
        """Test truncating text that is already shorter than max length."""
        # Arrange
        text = "This is a short text"
        max_length = 40

        # Act
        result = truncate_text(text, max_length=max_length)

        # Assert
        assert result == text
        assert len(result) == len(text)

    def test_truncate_long_text(self):
        """Test truncating text that is longer than max length."""
        # Arrange
        text = "This is a very long text that exceeds the maximum length limit"
        max_length = 20

        # Act
        result = truncate_text(text, max_length=max_length)

        # Assert
        assert result == "This is a very lo..."
        assert len(result) == max_length  # account for "..." replacing last 3 chars

    def test_truncate_with_default_max_length(self):
        """Test truncating text with default max length (40)."""
        # Arrange
        text = "This text is exactly 40 characters long."
        longer_text = (
            "This text is more than 40 characters long and should be truncated"
        )

        # Act
        result1 = truncate_text(text)
        result2 = truncate_text(longer_text)

        # Assert
        assert result1 == text  # No truncation
        assert result2 == "This text is more than 40 characters ..."
        assert len(result2) == 40  # 40 chars total including the "..."
