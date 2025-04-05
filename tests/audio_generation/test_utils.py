"""
Unit tests for the audio_generation.utils module.

This module tests utility functions for audio generation, including
audio level checking, concatenation, file loading, and text truncation.
"""

import io
import json
from datetime import datetime
from unittest.mock import MagicMock, call, mock_open, patch

import pytest
from pydub import AudioSegment

from audio_generation.utils import (
    check_audio_level,
    concatenate_audio_clips,
    create_output_folders,
    load_json_chunks,
    truncate_text,
)


class TestAudioLevelChecking:
    """Tests for audio level checking function."""

    def test_check_audio_level_with_valid_audio(self):
        """Test checking audio level with valid audio data."""
        # Arrange
        with patch("audio_generation.utils.AudioSegment") as mock_audio_segment:
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
        with patch("audio_generation.utils.AudioSegment") as mock_audio_segment:
            mock_audio_segment.from_mp3.side_effect = Exception("Invalid audio")
            audio_bytes = b"invalid_audio_data"

            # Act
            result = check_audio_level(audio_bytes)

            # Assert
            assert result is None


class TestConcatenateAudioClips:
    """Tests for audio clip concatenation function."""

    @pytest.fixture
    def mock_logger(self):
        """Fixture providing a mock logger."""
        with patch("audio_generation.utils.logger") as mock:
            yield mock

    def test_concatenate_single_clip(self, mock_logger):
        """Test concatenating a single audio clip."""
        # Arrange
        audio_clip = MagicMock(spec=AudioSegment)
        audio_clip.__len__.return_value = 1000  # 1 second duration
        output_path = "/path/to/output.mp3"

        with patch("audio_generation.utils.AudioSegment") as mock_audio_segment, patch(
            "builtins.open", mock_open()
        ) as mock_file, patch("os.path.exists") as mock_exists, patch(
            "os.path.getsize"
        ) as mock_getsize:

            # Setup mocks
            mock_empty = MagicMock()
            mock_audio_segment.empty.return_value = mock_empty
            mock_empty.__iadd__ = lambda self, other: audio_clip
            audio_clip.export = MagicMock()  # Explicitly define export method
            mock_audio_segment.from_mp3.return_value = audio_clip
            mock_exists.return_value = True
            mock_getsize.return_value = 1024  # 1KB

            # Act
            concatenate_audio_clips([audio_clip], output_path)

            # Assert
            mock_logger.info.assert_any_call("Audio export completed")
            mock_audio_segment.empty.assert_called_once()
            audio_clip.export.assert_called_once_with(output_path, format="mp3")

    def test_concatenate_multiple_clips(self, mock_logger):
        """Test concatenating multiple audio clips."""
        # Arrange
        audio_clip1 = MagicMock(spec=AudioSegment)
        audio_clip1.__len__.return_value = 1000  # 1 second duration
        audio_clip2 = MagicMock(spec=AudioSegment)
        audio_clip2.__len__.return_value = 500  # 0.5 seconds duration
        output_path = "/path/to/output.mp3"

        with patch("audio_generation.utils.AudioSegment") as mock_audio_segment, patch(
            "builtins.open", mock_open()
        ) as mock_file, patch("os.path.exists") as mock_exists, patch(
            "os.path.getsize"
        ) as mock_getsize:

            # Setup mocks
            mock_empty = MagicMock()
            mock_audio_segment.empty.return_value = mock_empty
            mock_empty.__iadd__ = lambda self, other: mock_empty
            mock_empty.export = MagicMock()  # Explicitly define export method
            mock_audio_segment.from_mp3.return_value = audio_clip1
            mock_exists.return_value = True
            mock_getsize.return_value = 1024  # 1KB

            # Act
            concatenate_audio_clips([audio_clip1, audio_clip2], output_path)

            # Assert
            mock_logger.info.assert_any_call("Audio export completed")
            mock_audio_segment.empty.assert_called_once()
            mock_empty.export.assert_called_once_with(output_path, format="mp3")

    def test_concatenate_with_gap(self, mock_logger):
        """Test concatenating audio clips with a gap."""
        # Arrange
        audio_clip1 = MagicMock(spec=AudioSegment)
        audio_clip1.__len__.return_value = 1000  # 1 second duration
        audio_clip2 = MagicMock(spec=AudioSegment)
        audio_clip2.__len__.return_value = 500  # 0.5 seconds duration
        gap_duration_ms = 200
        output_path = "/path/to/output.mp3"

        with patch("audio_generation.utils.AudioSegment") as mock_audio_segment, patch(
            "builtins.open", mock_open()
        ) as mock_file, patch("os.path.exists") as mock_exists, patch(
            "os.path.getsize"
        ) as mock_getsize:

            # Setup mocks
            mock_empty = MagicMock()
            mock_audio_segment.empty.return_value = mock_empty
            mock_empty.__iadd__ = lambda self, other: mock_empty
            mock_empty.export = MagicMock()  # Explicitly define export method

            mock_gap = MagicMock()
            mock_audio_segment.silent.return_value = mock_gap

            mock_audio_segment.from_mp3.return_value = audio_clip1
            mock_exists.return_value = True
            mock_getsize.return_value = 1024  # 1KB

            # Act
            concatenate_audio_clips(
                [audio_clip1, audio_clip2], output_path, gap_duration_ms=gap_duration_ms
            )

            # Assert
            mock_logger.info.assert_any_call(
                f"Adding {gap_duration_ms}ms gap between clips."
            )
            mock_audio_segment.silent.assert_called_once_with(duration=gap_duration_ms)
            mock_empty.export.assert_called_once_with(output_path, format="mp3")

    def test_concatenate_handles_errors(self, mock_logger):
        """Test error handling during concatenation."""
        # Arrange
        audio_clip = MagicMock(spec=AudioSegment)
        output_path = "/path/to/output.mp3"

        with patch("audio_generation.utils.AudioSegment") as mock_audio_segment:
            mock_empty = MagicMock()
            mock_audio_segment.empty.return_value = mock_empty
            mock_empty.__iadd__ = lambda self, other: mock_empty
            mock_empty.export.side_effect = Exception("Export failed")

            # Act and Assert
            with pytest.raises(Exception, match="Export failed"):
                concatenate_audio_clips([audio_clip], output_path)

            mock_logger.error.assert_called()


class TestLoadJsonChunks:
    """Tests for JSON chunks loading function."""

    def test_load_valid_json(self):
        """Test loading valid JSON chunks from a file."""
        # Arrange
        json_data = [
            {"type": "dialog", "text": "Hello"},
            {"type": "action", "text": "John walks"},
        ]
        json_str = json.dumps(json_data)

        with patch("builtins.open", mock_open(read_data=json_str)) as mock_file:
            # Act
            result = load_json_chunks("test_file.json")

            # Assert
            mock_file.assert_called_once_with("test_file.json", "r", encoding="utf-8")
            assert len(result) == 2
            assert result[0]["type"] == "dialog"
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


class TestCreateOutputFolders:
    """Tests for output folders creation function."""

    @patch("os.makedirs")
    @patch("audio_generation.utils.datetime")
    def test_create_output_folders(self, mock_datetime, mock_makedirs):
        """Test creating output folders."""
        # Arrange
        mock_datetime.now.return_value = datetime(2023, 1, 1, 12, 0, 0)
        input_file = "input/screenplay.json"

        # Act
        main_folder, cache_folder, output_file, log_file = create_output_folders(
            input_file
        )

        # Assert
        assert main_folder == "output/screenplay"
        assert cache_folder == "output/screenplay/cache"
        assert output_file == "output/screenplay/screenplay.mp3"
        assert log_file == "output/screenplay/logs/log_20230101_120000.txt"

        mock_makedirs.assert_any_call("output/screenplay/cache", exist_ok=True)
        mock_makedirs.assert_any_call("output/screenplay/logs", exist_ok=True)

    @patch("os.makedirs")
    @patch("audio_generation.utils.datetime")
    def test_create_output_folders_with_run_mode(self, mock_datetime, mock_makedirs):
        """Test creating output folders with run mode specified."""
        # Arrange
        mock_datetime.now.return_value = datetime(2023, 1, 1, 12, 0, 0)
        input_file = "input/screenplay.json"
        run_mode = "dry-run"

        # Act
        main_folder, cache_folder, output_file, log_file = create_output_folders(
            input_file, run_mode
        )

        # Assert
        assert main_folder == "output/screenplay"
        assert cache_folder == "output/screenplay/cache"
        assert output_file == "output/screenplay/screenplay.mp3"
        assert log_file == "output/screenplay/logs/[dry-run]_log_20230101_120000.txt"

        mock_makedirs.assert_any_call("output/screenplay/cache", exist_ok=True)
        mock_makedirs.assert_any_call("output/screenplay/logs", exist_ok=True)

    @patch("os.makedirs")
    def test_create_output_folders_handles_errors(self, mock_makedirs):
        """Test error handling when creating output folders."""
        # Arrange
        mock_makedirs.side_effect = OSError("Failed to create directory")
        input_file = "input/screenplay.json"

        # Act and Assert
        with pytest.raises(OSError, match="Failed to create directory"):
            create_output_folders(input_file)


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
