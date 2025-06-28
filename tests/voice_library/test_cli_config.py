"""Tests for the voice library configuration CLI."""

from unittest.mock import patch

import pytest

from script_to_speech.voice_library.cli_config import main


@patch("script_to_speech.voice_library.cli_config.load_config")
@patch("script_to_speech.voice_library.cli_config.get_conflicting_ids")
@patch("sys.exit")
def test_cli_config_no_config(mock_exit, mock_get_conflicting_ids, mock_load_config):
    """Tests the CLI when no configuration files are found."""
    # Arrange
    mock_load_config.return_value = {}
    mock_get_conflicting_ids.return_value = {}

    # Act
    main()

    # Assert
    mock_exit.assert_called_once_with(0)


@patch("script_to_speech.voice_library.cli_config.load_config")
@patch("script_to_speech.voice_library.cli_config.get_conflicting_ids")
@patch("script_to_speech.voice_library.cli_config.get_empty_include_lists")
@patch("sys.exit")
def test_cli_config_no_conflicts(
    mock_exit, mock_get_empty_include_lists, mock_get_conflicting_ids, mock_load_config
):
    """Tests the CLI when configurations are loaded and no conflicts are found."""
    # Arrange
    mock_load_config.return_value = {"some_key": "some_value"}
    mock_get_conflicting_ids.return_value = {}
    mock_get_empty_include_lists.return_value = {}

    # Act
    main()

    # Assert
    mock_exit.assert_called_once_with(0)


@patch("script_to_speech.voice_library.cli_config.load_config")
@patch("script_to_speech.voice_library.cli_config.get_conflicting_ids")
@patch("script_to_speech.voice_library.cli_config.get_empty_include_lists")
@patch("sys.exit")
def test_cli_config_with_conflicts(
    mock_exit, mock_get_empty_include_lists, mock_get_conflicting_ids, mock_load_config
):
    """Tests the CLI when configurations are loaded and conflicts are found."""
    # Arrange
    mock_load_config.return_value = {"some_key": "some_value"}
    mock_get_conflicting_ids.return_value = {"openai": {"alloy"}}
    mock_get_empty_include_lists.return_value = {}

    # Act
    main()

    # Assert
    mock_exit.assert_called_once_with(1)


@patch("script_to_speech.voice_library.cli_config.load_config")
@patch("script_to_speech.voice_library.cli_config.get_conflicting_ids")
@patch("script_to_speech.voice_library.cli_config.get_empty_include_lists")
@patch("sys.exit")
def test_cli_config_with_empty_include_lists(
    mock_exit, mock_get_empty_include_lists, mock_get_conflicting_ids, mock_load_config
):
    """Tests the CLI when configurations are loaded and empty include lists are found."""
    # Arrange
    mock_load_config.return_value = {"some_key": "some_value"}
    mock_get_conflicting_ids.return_value = {}
    mock_get_empty_include_lists.return_value = {"openai": []}

    # Act
    main()

    # Assert
    mock_exit.assert_called_once_with(1)
