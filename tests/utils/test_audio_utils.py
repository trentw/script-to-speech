import io
import os
from unittest.mock import MagicMock, Mock, patch

import pytest
from pydub import AudioSegment

from script_to_speech.utils.audio_utils import (
    configure_ffmpeg,
    export_audio_segment,
    split_audio_on_silence,
)


class TestConfigureFFmpeg:
    """Tests for the configure_ffmpeg function."""

    @patch("script_to_speech.utils.audio_utils.os.path.exists")
    @patch("script_to_speech.utils.audio_utils.os.access")
    @patch("script_to_speech.utils.audio_utils.AudioSegment.silent")
    @patch("script_to_speech.utils.audio_utils.os.remove")
    def test_configure_ffmpeg_with_directory_path(
        self, mock_remove, mock_silent, mock_access, mock_exists
    ):
        """Test configuring ffmpeg with a directory path."""
        # Setup mocks
        mock_exists.return_value = True
        mock_access.return_value = True
        mock_silent.return_value = MagicMock()
        mock_silent.return_value.export.return_value = None

        # Mock environmental PATH
        with patch.dict("os.environ", {"PATH": "/original/path"}):
            # Call function with directory path
            configure_ffmpeg("/test/ffmpeg/path")

            # Check that path was added to PATH
            assert "/test/ffmpeg/path" in os.environ["PATH"]

            # Verify the existence and executability checks were performed without checking specific paths
            assert mock_exists.call_count >= 2
            assert mock_access.call_count >= 2

            # Check that pydub was configured
            assert "ffmpeg" in AudioSegment.converter
            assert "ffmpeg" in AudioSegment.ffmpeg
            assert "ffprobe" in AudioSegment.ffprobe

            # Check that verification test was performed
            mock_silent.assert_called_once()
            mock_silent.return_value.export.assert_called_once_with(
                "test.mp3", format="mp3"
            )
            mock_remove.assert_called_once_with("test.mp3")

    @patch("script_to_speech.utils.audio_utils.os.path.exists")
    @patch("script_to_speech.utils.audio_utils.os.access")
    @patch("script_to_speech.utils.audio_utils.AudioSegment.silent")
    @patch("script_to_speech.utils.audio_utils.os.remove")
    def test_configure_ffmpeg_with_direct_executable_path(
        self, mock_remove, mock_silent, mock_access, mock_exists
    ):
        """Test configuring ffmpeg with a direct executable path."""
        # Setup mocks
        mock_exists.return_value = True
        mock_access.return_value = True
        mock_silent.return_value = MagicMock()
        mock_silent.return_value.export.return_value = None

        # Mock environmental PATH
        with patch.dict("os.environ", {"PATH": "/original/path"}):
            # Mock os.path.isdir to return False (not a directory)
            with patch("script_to_speech.utils.audio_utils.os.path.isdir", return_value=False):
                # Mock os.path.dirname to return directory
                with patch(
                    "script_to_speech.utils.audio_utils.os.path.dirname",
                    return_value="/test/ffmpeg/path",
                ):
                    # Call function with executable path
                    configure_ffmpeg("/test/ffmpeg/path/ffmpeg")

                    # Check that path was added to PATH
                    assert "/test/ffmpeg/path" in os.environ["PATH"]

                    # Verify the existence and executability checks were performed
                    assert mock_exists.call_count >= 2
                    assert mock_access.call_count >= 2

                    # Check that pydub was configured
                    assert "ffmpeg" in AudioSegment.converter
                    assert "ffmpeg" in AudioSegment.ffmpeg
                    assert "ffprobe" in AudioSegment.ffprobe

    @patch("script_to_speech.utils.audio_utils.os.path.exists")
    def test_configure_ffmpeg_executable_not_found(self, mock_exists):
        """Test configure_ffmpeg raises ValueError when executable not found."""
        # Setup mock to return False (file doesn't exist)
        mock_exists.return_value = False

        # Call should raise ValueError
        with pytest.raises(ValueError, match="Executable not found:"):
            configure_ffmpeg("/test/ffmpeg/path")

    @patch("script_to_speech.utils.audio_utils.os.path.exists")
    @patch("script_to_speech.utils.audio_utils.os.access")
    def test_configure_ffmpeg_executable_not_executable(self, mock_access, mock_exists):
        """Test configure_ffmpeg raises ValueError when file is not executable."""
        # Setup mocks
        mock_exists.return_value = True
        mock_access.return_value = False  # Not executable

        # Call should raise ValueError
        with pytest.raises(ValueError, match="File is not executable:"):
            configure_ffmpeg("/test/ffmpeg/path")

    @patch("script_to_speech.utils.audio_utils.os.path.exists")
    @patch("script_to_speech.utils.audio_utils.os.access")
    @patch("script_to_speech.utils.audio_utils.AudioSegment.silent")
    def test_configure_ffmpeg_verification_error(
        self, mock_silent, mock_access, mock_exists
    ):
        """Test configure_ffmpeg raises RuntimeError when verification fails."""
        # Setup mocks
        mock_exists.return_value = True
        mock_access.return_value = True
        mock_silent.side_effect = Exception("Test error")

        # Call should raise RuntimeError
        with pytest.raises(RuntimeError, match="Failed to verify ffmpeg installation"):
            configure_ffmpeg("/test/ffmpeg/path")

    @patch("script_to_speech.utils.audio_utils.AudioSegment.silent")
    @patch("script_to_speech.utils.audio_utils.os.remove")
    def test_configure_ffmpeg_with_none(self, mock_remove, mock_silent):
        """Test configuring ffmpeg with None as path."""
        # Setup mocks
        mock_silent.return_value = MagicMock()
        mock_silent.return_value.export.return_value = None

        # Call function with None (should use system ffmpeg)
        configure_ffmpeg(None)

        # Check that verification test was performed
        mock_silent.assert_called_once()
        mock_silent.return_value.export.assert_called_once_with(
            "test.mp3", format="mp3"
        )
        mock_remove.assert_called_once_with("test.mp3")


class TestSplitAudioOnSilence:
    """Tests for the split_audio_on_silence function."""

    @patch("script_to_speech.utils.audio_utils.AudioSegment.from_mp3")
    @patch("script_to_speech.utils.audio_utils.detect_silence")
    def test_split_audio_on_silence_success(self, mock_detect_silence, mock_from_mp3):
        """Test split_audio_on_silence with successful split."""
        # Setup mocks
        mock_audio = MagicMock()
        mock_from_mp3.return_value = mock_audio
        mock_audio.__len__.return_value = 10000  # 10 seconds

        # Mock silence detection - return a silence range from 2-3 seconds
        mock_detect_silence.return_value = [(2000, 3000)]

        # Test audio data
        audio_data = b"test audio data"

        # Call function
        result = split_audio_on_silence(
            audio_data, min_silence_len=350, silence_thresh=-20, keep_silence=700
        )

        # Check that audio was loaded
        mock_from_mp3.assert_called_once()

        # Check that silence was detected
        mock_detect_silence.assert_called_once_with(
            mock_audio,
            min_silence_len=350,
            silence_thresh=-20,
            seek_step=1,
        )

        # Check that audio was split at end of first silence minus keep_silence
        mock_audio.__getitem__.assert_called_once_with(slice(2300, None, None))

        # Check that result is the sliced audio
        assert result == mock_audio.__getitem__.return_value

    def test_split_audio_on_silence_empty_audio(self):
        """Test split_audio_on_silence with empty audio data."""
        # Call with empty data should raise ValueError
        with pytest.raises(ValueError, match="Empty audio data provided"):
            split_audio_on_silence(b"")

    @patch("script_to_speech.utils.audio_utils.AudioSegment.from_mp3")
    @patch("script_to_speech.utils.audio_utils.detect_silence")
    def test_split_audio_on_silence_no_silence_detected(
        self, mock_detect_silence, mock_from_mp3
    ):
        """Test split_audio_on_silence when no silence is detected."""
        # Setup mocks
        mock_audio = MagicMock()
        mock_from_mp3.return_value = mock_audio

        # Mock silence detection - return empty list (no silence)
        mock_detect_silence.return_value = []

        # Test audio data
        audio_data = b"test audio data"

        # Call function
        result = split_audio_on_silence(audio_data)

        # Check that silence was detected
        mock_detect_silence.assert_called_once()

        # Check that result is None (no split performed)
        assert result is None

    @patch("script_to_speech.utils.audio_utils.AudioSegment.from_mp3")
    @patch("script_to_speech.utils.audio_utils.detect_silence")
    def test_split_audio_on_silence_split_point_beyond_audio_length(
        self, mock_detect_silence, mock_from_mp3
    ):
        """Test split_audio_on_silence when split point would be beyond audio length."""
        # Setup mocks
        mock_audio = MagicMock()
        mock_from_mp3.return_value = mock_audio
        mock_audio.__len__.return_value = 5000  # 5 seconds

        # Mock silence detection - return a silence range that ends at 5000 (end of audio)
        mock_detect_silence.return_value = [(4000, 5000)]

        # Set up __getitem__ to return a mock result for any slice
        mock_result = MagicMock()
        mock_audio.__getitem__.return_value = mock_result

        # Test audio data
        audio_data = b"test audio data"

        # Call the function with various keep_silence values
        result = split_audio_on_silence(audio_data, keep_silence=700)

        # For any valid split point, should return the sliced audio
        assert result == mock_result

    @patch("script_to_speech.utils.audio_utils.AudioSegment.from_mp3")
    def test_split_audio_on_silence_error_handling(self, mock_from_mp3):
        """Test split_audio_on_silence error handling."""
        # Setup mock to raise exception
        mock_from_mp3.side_effect = Exception("Test error")

        # Test audio data
        audio_data = b"test audio data"

        # Call should raise RuntimeError
        with pytest.raises(RuntimeError, match="Failed to process audio:"):
            split_audio_on_silence(audio_data)


class TestExportAudioSegment:
    """Tests for the export_audio_segment function."""

    @patch("script_to_speech.utils.audio_utils.os.makedirs")
    def test_export_audio_segment_success(self, mock_makedirs):
        """Test export_audio_segment with successful export."""
        # Setup mock audio segment
        mock_audio = MagicMock()

        # Setup mock to indicate file was created
        with patch("script_to_speech.utils.audio_utils.os.path.exists", return_value=True):
            # Call function
            export_audio_segment(mock_audio, "/test/output/path.mp3")

            # Check that directory was created
            mock_makedirs.assert_called_once_with("/test/output", exist_ok=True)

            # Check that audio was exported
            mock_audio.export.assert_called_once_with(
                "/test/output/path.mp3", format="mp3"
            )

    def test_export_audio_segment_none_audio(self):
        """Test export_audio_segment with None audio segment."""
        # Call with None audio should raise ValueError
        with pytest.raises(ValueError, match="No audio segment provided"):
            export_audio_segment(None, "/test/output/path.mp3")

    def test_export_audio_segment_empty_path(self):
        """Test export_audio_segment with empty output path."""
        # Setup mock audio segment
        mock_audio = MagicMock()

        # Call with empty path should raise ValueError
        with pytest.raises(ValueError, match="No output path provided"):
            export_audio_segment(mock_audio, "")

    @patch("script_to_speech.utils.audio_utils.os.makedirs")
    def test_export_audio_segment_export_error(self, mock_makedirs):
        """Test export_audio_segment when export fails."""
        # Setup mock audio segment with export that raises exception
        mock_audio = MagicMock()
        mock_audio.export.side_effect = Exception("Export error")

        # Call should raise RuntimeError
        with pytest.raises(RuntimeError, match="Failed to export audio:"):
            export_audio_segment(mock_audio, "/test/output/path.mp3")

    @patch("script_to_speech.utils.audio_utils.os.makedirs")
    def test_export_audio_segment_file_not_created(self, mock_makedirs):
        """Test export_audio_segment when file is not created after export."""
        # Setup mock audio segment
        mock_audio = MagicMock()

        # Setup mock to indicate file was not created
        with patch("script_to_speech.utils.audio_utils.os.path.exists", return_value=False):
            # Call should raise RuntimeError
            with pytest.raises(
                RuntimeError, match="Export completed but file was not created"
            ):
                export_audio_segment(mock_audio, "/test/output/path.mp3")

    @patch("script_to_speech.utils.audio_utils.os.makedirs")
    def test_export_audio_segment_with_custom_format(self, mock_makedirs):
        """Test export_audio_segment with custom format."""
        # Setup mock audio segment
        mock_audio = MagicMock()

        # Setup mock to indicate file was created
        with patch("script_to_speech.utils.audio_utils.os.path.exists", return_value=True):
            # Call function with custom format
            export_audio_segment(mock_audio, "/test/output/path.wav", format="wav")

            # Check that audio was exported with correct format
            mock_audio.export.assert_called_once_with(
                "/test/output/path.wav", format="wav"
            )
