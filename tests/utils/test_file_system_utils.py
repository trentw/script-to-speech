"""Tests for file_system_utils.py."""

import os
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from script_to_speech.utils.file_system_utils import (
    create_output_folders,
    sanitize_name,
)


class TestSanitizeName:
    """Tests for sanitize_name function."""

    def test_sanitize_name(self):
        """Test sanitizing names for use in filenames."""
        # Test basic sanitization
        assert sanitize_name("Hello World!") == "Hello_World"

        # Test with special characters
        assert sanitize_name("My@Screenplay#123") == "MyScreenplay123"

        # Test with multiple spaces and hyphens
        assert sanitize_name("This - is  a   test") == "This_is_a_test"

        # Test with leading/trailing spaces
        assert (
            sanitize_name(" leading and trailing spaces ")
            == "leading_and_trailing_spaces"
        )

        # Test with empty string
        assert sanitize_name("") == ""


class TestCreateOutputFolders:
    """Tests for output folders creation function."""

    @patch("pathlib.Path.mkdir")
    @patch("script_to_speech.utils.file_system_utils.datetime")
    def test_create_output_folders_basic(self, mock_datetime, mock_mkdir):
        """Test basic functionality of create_output_folders."""
        # Arrange
        mock_datetime.now.return_value = datetime(2023, 1, 1, 12, 0, 0)
        input_file = "input/test_screenplay.fountain"

        # Act
        main_output_folder, cache_folder, logs_folder, log_file = create_output_folders(
            input_file
        )

        # Assert
        assert main_output_folder == Path("output/test_screenplay")
        assert cache_folder == Path("output/test_screenplay/cache")
        assert logs_folder == Path("output/test_screenplay/logs")
        assert log_file == Path("output/test_screenplay/logs/log_20230101_120000.txt")

        # Verify mkdir was called for each directory
        assert mock_mkdir.call_count == 3
        # We can't directly check the exact calls because Path objects are created inside the function
        # But we can verify the function was called with the expected arguments
        for call in mock_mkdir.call_args_list:
            args, kwargs = call
            assert kwargs == {"parents": True, "exist_ok": True}

    @patch("pathlib.Path.mkdir")
    @patch("script_to_speech.utils.file_system_utils.datetime")
    def test_create_output_folders_with_run_mode(self, mock_datetime, mock_mkdir):
        """Test create_output_folders with run mode."""
        # Arrange
        mock_datetime.now.return_value = datetime(2023, 1, 1, 12, 0, 0)
        input_file = "input/test_screenplay.fountain"
        run_mode = "test_mode"

        # Act
        main_output_folder, cache_folder, logs_folder, log_file = create_output_folders(
            input_file, run_mode
        )

        # Assert
        assert main_output_folder == Path("output/test_screenplay")
        assert cache_folder == Path("output/test_screenplay/cache")
        assert logs_folder == Path("output/test_screenplay/logs")
        assert log_file == Path(
            "output/test_screenplay/logs/[test_mode]_log_20230101_120000.txt"
        )

        # Verify mkdir was called for each directory
        assert mock_mkdir.call_count == 3

    @patch("pathlib.Path.mkdir")
    @patch("script_to_speech.utils.file_system_utils.datetime")
    def test_create_output_folders_with_dummy_override(self, mock_datetime, mock_mkdir):
        """Test create_output_folders with dummy provider override."""
        # Arrange
        mock_datetime.now.return_value = datetime(2023, 1, 1, 12, 0, 0)
        input_file = "input/test_screenplay.fountain"
        dummy_provider_override = True

        # Act
        main_output_folder, cache_folder, logs_folder, log_file = create_output_folders(
            input_file, dummy_provider_override=dummy_provider_override
        )

        # Assert
        assert main_output_folder == Path("output/test_screenplay")
        assert cache_folder == Path("output/test_screenplay/dummy_cache")
        assert logs_folder == Path("output/test_screenplay/logs")
        assert log_file == Path(
            "output/test_screenplay/logs/[dummy]log_20230101_120000.txt"
        )

        # Verify mkdir was called for each directory
        assert mock_mkdir.call_count == 3

    @patch("pathlib.Path.mkdir")
    @patch("script_to_speech.utils.file_system_utils.datetime")
    def test_create_output_folders_with_run_mode_and_dummy_override(
        self, mock_datetime, mock_mkdir
    ):
        """Test create_output_folders with both run mode and dummy provider override."""
        # Arrange
        mock_datetime.now.return_value = datetime(2023, 1, 1, 12, 0, 0)
        input_file = "input/test_screenplay.fountain"
        run_mode = "test_mode"
        dummy_provider_override = True

        # Act
        main_output_folder, cache_folder, logs_folder, log_file = create_output_folders(
            input_file, run_mode, dummy_provider_override
        )

        # Assert
        assert main_output_folder == Path("output/test_screenplay")
        assert cache_folder == Path("output/test_screenplay/dummy_cache")
        assert logs_folder == Path("output/test_screenplay/logs")
        assert log_file == Path(
            "output/test_screenplay/logs/[dummy][test_mode]_log_20230101_120000.txt"
        )

        # Verify mkdir was called for each directory
        assert mock_mkdir.call_count == 3

    @patch("pathlib.Path.mkdir")
    def test_create_output_folders_handles_errors(self, mock_mkdir):
        """Test error handling when creating output folders."""
        # Arrange
        mock_mkdir.side_effect = OSError("Failed to create directory")
        input_file = "input/test_screenplay.fountain"

        # Act and Assert
        with pytest.raises(OSError, match="Failed to create directory"):
            create_output_folders(input_file)
