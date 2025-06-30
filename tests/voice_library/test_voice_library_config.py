"""Tests for voice library configuration loading and merging."""

from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest
import yaml

from script_to_speech.utils.dict_utils import deep_merge
from script_to_speech.voice_library.voice_library_config import load_config


@pytest.fixture
def mock_yaml_files(mocker):
    """Mocks the file system and yaml loading for config files completely."""
    # Arrange
    user_inclusion_content = yaml.dump({"included_sts_ids": {"elevenlabs": ["sully"]}})
    user_exclusion_content = yaml.dump(
        {"excluded_sts_ids": {"openai": ["alloy", "nova"]}}
    )
    repo_exclusion_content = yaml.dump(
        {"excluded_sts_ids": {"openai": ["echo"], "cartesia": ["voice-1"]}}
    )

    # Create mock file paths that will be returned by find_yaml_files
    user_path1 = Path("/mock/user/inclusions.yaml")
    user_path2 = Path("/mock/user/exclusions.yaml")
    repo_path1 = Path("/mock/repo/repo_exclusions.yaml")

    mock_paths = {
        user_path1: user_inclusion_content,
        user_path2: user_exclusion_content,
        repo_path1: repo_exclusion_content,
    }

    # Mock the path constants to use test-specific paths
    mock_repo_path = Path("/mock/repo")
    mock_user_path = Path("/mock/user")

    mocker.patch(
        "script_to_speech.voice_library.voice_library_config.REPO_CONFIG_PATH",
        mock_repo_path,
    )
    mocker.patch(
        "script_to_speech.voice_library.voice_library_config.USER_CONFIG_PATH",
        mock_user_path,
    )

    # Mock find_yaml_files to return specific paths based on the directory being searched
    def mock_find_yaml_files(directory):
        if directory == mock_repo_path:
            return [repo_path1]
        elif directory == mock_user_path:
            return [user_path1, user_path2]
        return []

    mocker.patch(
        "script_to_speech.voice_library.voice_library_config.find_yaml_files",
        side_effect=mock_find_yaml_files,
    )

    # Mock open to return the correct content for each path
    def open_side_effect(path, *args, **kwargs):
        path_obj = Path(path)
        if path_obj in mock_paths:
            return mock_open(read_data=mock_paths[path_obj])(*args, **kwargs)
        raise FileNotFoundError(path)

    mocker.patch("builtins.open", side_effect=open_side_effect)


def test_deep_merge():
    """Tests that dictionaries are merged correctly, especially lists."""
    # Arrange
    d1 = {
        "included_sts_ids": {"openai": ["shimmer"]},
        "excluded_sts_ids": {"elevenlabs": ["dave"]},
        "other_property": "value1",
    }
    d2 = {
        "included_sts_ids": {"openai": ["fable"], "elevenlabs": ["sully"]},
        "excluded_sts_ids": {"elevenlabs": ["bob"]},
        "new_property": "value2",
    }

    # Act
    merged = deep_merge(d1, d2)

    # Assert
    assert sorted(merged["included_sts_ids"]["openai"]) == ["fable", "shimmer"]
    assert merged["included_sts_ids"]["elevenlabs"] == ["sully"]
    assert sorted(merged["excluded_sts_ids"]["elevenlabs"]) == ["bob", "dave"]
    assert merged["other_property"] == "value1"  # Should not be overwritten
    assert merged["new_property"] == "value2"


def test_load_config_merges_files_correctly(mock_yaml_files):
    """Tests that load_config finds, reads, and merges YAML files as expected."""
    # Act
    config = load_config()

    # Assert
    assert "included_sts_ids" in config
    assert "excluded_sts_ids" in config

    # Check included IDs from user file
    assert config["included_sts_ids"]["elevenlabs"] == ["sully"]

    # Check excluded IDs from both user and repo files (should be merged)
    assert "openai" in config["excluded_sts_ids"]
    assert "cartesia" in config["excluded_sts_ids"]
    assert sorted(config["excluded_sts_ids"]["openai"]) == ["alloy", "echo", "nova"]
    assert config["excluded_sts_ids"]["cartesia"] == ["voice-1"]


def test_load_config_calls_expected_functions(mocker):
    """Tests that load_config calls the expected filesystem functions (verifies mocking coverage)."""
    # Arrange - Mock all the functions that load_config should call
    mock_find_yaml_files = mocker.patch(
        "script_to_speech.voice_library.voice_library_config.find_yaml_files",
        return_value=[],
    )

    # Act
    config = load_config()

    # Assert - Verify the mocked functions were called as expected
    assert (
        mock_find_yaml_files.call_count == 2
    )  # Called for both REPO_CONFIG_PATH and USER_CONFIG_PATH
    assert isinstance(config, dict)
    assert config == {}  # Should be empty when no files are found
