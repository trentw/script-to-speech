"""Integration tests for file_system_utils.py."""

import os
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from script_to_speech.utils.file_system_utils import create_output_folders


@pytest.mark.integration
@patch("pathlib.Path.mkdir")
@patch("pathlib.Path.exists")
@patch("script_to_speech.utils.file_system_utils.datetime")
def test_create_output_folders_integration(mock_datetime, mock_exists, mock_mkdir):
    """Integration test for create_output_folders function."""
    # Arrange
    mock_datetime.now.return_value = datetime(2023, 1, 1, 12, 0, 0)
    input_file = "input/test_screenplay.fountain"

    # Setup mock exists to return True for all paths
    mock_exists.return_value = True

    # Call the function
    main_output_folder, cache_folder, logs_folder, log_file = create_output_folders(
        input_file, run_mode="test_mode"
    )

    # Check path relationships (environment-independent)
    assert main_output_folder.name == "test_screenplay"
    assert main_output_folder.parent.name == "output"
    assert cache_folder.name == "cache"
    assert cache_folder.parent == main_output_folder
    assert logs_folder.name == "logs"
    assert logs_folder.parent == main_output_folder

    # Check that the log file path is correct
    assert log_file.parent == logs_folder
    assert "[test_mode]_" in log_file.name
    assert log_file.suffix == ".txt"
    assert "20230101_120000" in log_file.name

    # Verify mkdir was called for each directory
    assert mock_mkdir.call_count == 3

    # Test with dummy provider override
    mock_mkdir.reset_mock()
    main_output_folder, cache_folder, logs_folder, log_file = create_output_folders(
        input_file, run_mode="test_mode", dummy_provider_override=True
    )

    # Check that the cache folder name includes "dummy_"
    assert "dummy_cache" in str(cache_folder)
    # Check that the log file name includes "[dummy]"
    assert "[dummy]" in log_file.name

    # Verify mkdir was called for each directory again
    assert mock_mkdir.call_count == 3


@pytest.mark.integration
@patch("pathlib.Path.mkdir")
def test_create_output_folders_integration_error_handling(mock_mkdir):
    """Test error handling in integration context."""
    # Arrange
    mock_mkdir.side_effect = OSError("Failed to create directory")
    input_file = "input/test_screenplay.fountain"

    # Act and Assert
    with pytest.raises(OSError, match="Failed to create directory"):
        create_output_folders(input_file)
