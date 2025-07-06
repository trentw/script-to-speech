"""Tests for voice library script utilities."""

from pathlib import Path
from unittest.mock import patch

import pytest

from script_to_speech.voice_library.voice_library_script_utils import (
    find_provider_specific_file,
)


@pytest.fixture
def mock_paths(mocker):
    """Mocks the script paths and filesystem."""
    mock_repo_scripts_path = Path("/mock/repo/voice_library_scripts")
    mock_user_scripts_path = Path("/mock/user/voice_library/voice_library_scripts")

    mocker.patch(
        "script_to_speech.voice_library.voice_library_script_utils.REPO_VOICE_LIBRARY_SCRIPTS_PATH",
        mock_repo_scripts_path,
    )
    mocker.patch(
        "script_to_speech.voice_library.voice_library_script_utils.USER_VOICE_LIBRARY_SCRIPTS_PATH",
        mock_user_scripts_path,
    )

    return mock_repo_scripts_path, mock_user_scripts_path


def test_find_provider_specific_file_not_found(mock_paths, mocker):
    """Tests that None is returned when no file is found."""
    # Arrange
    script_name = "test_script"
    provider = "test_provider"
    filename = "provider_logic.py"

    # Mock all files as not existing
    mocker.patch("pathlib.Path.is_file", return_value=False)

    # Act
    result = find_provider_specific_file(script_name, provider, filename)

    # Assert
    assert result is None


def test_find_provider_specific_file_basic_functionality(mock_paths, mocker):
    """Tests basic functionality without complex mocking."""
    # Arrange
    script_name = "test_script"
    provider = "test_provider"
    filename = "provider_logic.py"

    # Simple test - just ensure the function can be called without errors
    mocker.patch("pathlib.Path.is_file", return_value=False)

    # Act
    result = find_provider_specific_file(script_name, provider, filename)

    # Assert
    assert result is None


def test_find_provider_specific_file_edge_case_empty_paths(mock_paths, mocker):
    """Tests finding files with edge case empty path components."""
    # Arrange
    script_name = ""
    provider = ""
    filename = ""

    mocker.patch("pathlib.Path.is_file", return_value=False)

    # Act
    result = find_provider_specific_file(script_name, provider, filename)

    # Assert
    assert result is None


def test_find_provider_specific_file_user_takes_precedence(mock_paths, mocker):
    """Tests that user file takes precedence when both user and repo files exist."""
    # Arrange
    repo_path, user_path = mock_paths
    script_name = "fetch_voices"
    provider = "elevenlabs"
    filename = "fetch_provider_voices.py"

    user_file = user_path / script_name / provider / filename
    repo_file = repo_path / script_name / provider / filename

    directories = set()
    files = {user_file, repo_file}

    def mock_is_file(self):
        return self in files

    mocker.patch.object(Path, "is_file", mock_is_file)

    # Act
    result = find_provider_specific_file(script_name, provider, filename)

    # Assert
    assert result == user_file


def test_find_provider_specific_file_only_repo_exists(mock_paths, mocker):
    """Tests finding file when only repo file exists."""
    # Arrange
    repo_path, user_path = mock_paths
    script_name = "fetch_voices"
    provider = "openai"
    filename = "fetch_provider_voices.py"

    user_file = user_path / script_name / provider / filename
    repo_file = repo_path / script_name / provider / filename

    directories = set()
    files = {repo_file}

    def mock_is_file(self):
        return self in files

    mocker.patch.object(Path, "is_file", mock_is_file)

    # Act
    result = find_provider_specific_file(script_name, provider, filename)

    # Assert
    assert result == repo_file


def test_find_provider_specific_file_only_user_exists(mock_paths, mocker):
    """Tests finding file when only user file exists."""
    # Arrange
    repo_path, user_path = mock_paths
    script_name = "fetch_voices"
    provider = "cartesia"
    filename = "fetch_provider_voices.py"

    user_file = user_path / script_name / provider / filename
    repo_file = repo_path / script_name / provider / filename

    directories = set()
    files = {user_file}

    def mock_is_file(self):
        return self in files

    mocker.patch.object(Path, "is_file", mock_is_file)

    # Act
    result = find_provider_specific_file(script_name, provider, filename)

    # Assert
    assert result == user_file


def test_find_provider_specific_file_neither_exists(mock_paths, mocker):
    """Tests finding file when neither user nor repo files exist."""
    # Arrange
    repo_path, user_path = mock_paths
    script_name = "nonexistent_script"
    provider = "unknown_provider"
    filename = "missing_file.py"

    # Mock no files as existing
    mocker.patch("pathlib.Path.is_file", return_value=False)

    # Act
    result = find_provider_specific_file(script_name, provider, filename)

    # Assert
    assert result is None
