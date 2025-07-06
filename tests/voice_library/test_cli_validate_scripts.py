"""Tests for the voice library script validator CLI."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from script_to_speech.voice_library.cli_validate_scripts import (
    main,
    validate_scripts,
)


@pytest.fixture
def mock_script_paths(mocker):
    """Mocks the script paths for validation."""
    mock_repo_path = Path("/mock/repo/voice_library_scripts")
    mock_user_path = Path("/mock/user/voice_library/voice_library_scripts")

    mocker.patch(
        "script_to_speech.voice_library.cli_validate_scripts.REPO_VOICE_LIBRARY_SCRIPTS_PATH",
        mock_repo_path,
    )
    mocker.patch(
        "script_to_speech.voice_library.cli_validate_scripts.USER_VOICE_LIBRARY_SCRIPTS_PATH",
        mock_user_path,
    )

    return mock_repo_path, mock_user_path


def test_validate_scripts_empty_directories(mock_script_paths, mocker):
    """Tests validation with empty directories."""
    # Arrange
    repo_path, user_path = mock_script_paths

    # Mock the directory checks to return True but empty iterdir
    mocker.patch("pathlib.Path.is_dir", return_value=True)
    mocker.patch("pathlib.Path.iterdir", return_value=[])

    # Act
    is_valid = validate_scripts(project_only=False)

    # Assert
    assert is_valid is True


def test_validate_scripts_nonexistent_directories(mock_script_paths, mocker):
    """Tests validation with non-existent directories."""
    # Arrange
    repo_path, user_path = mock_script_paths

    # Mock the directory checks to return False
    mocker.patch("pathlib.Path.is_dir", return_value=False)

    # Act
    is_valid = validate_scripts(project_only=False)

    # Assert
    assert is_valid is True


@patch("sys.argv", ["sts-validate-voice-library-scripts"])
@patch("script_to_speech.voice_library.cli_validate_scripts.validate_scripts")
def test_main_success(mock_validate_scripts):
    """Tests the main function of the validator CLI."""
    # Arrange
    mock_validate_scripts.return_value = True

    # Act
    result = main()

    # Assert
    assert result == 0
    mock_validate_scripts.assert_called_once_with(False)


@patch("sys.argv", ["sts-validate-voice-library-scripts", "--project-only"])
@patch("script_to_speech.voice_library.cli_validate_scripts.validate_scripts")
def test_main_project_only(mock_validate_scripts):
    """Tests the main function with project-only flag."""
    # Arrange
    mock_validate_scripts.return_value = True

    # Act
    result = main()

    # Assert
    assert result == 0
    mock_validate_scripts.assert_called_once_with(True)


@patch("sys.argv", ["sts-validate-voice-library-scripts"])
@patch("script_to_speech.voice_library.cli_validate_scripts.validate_scripts")
def test_main_validation_failure(mock_validate_scripts):
    """Tests the main function when validation fails."""
    # Arrange
    mock_validate_scripts.return_value = False

    # Act
    result = main()

    # Assert
    assert result == 1
    mock_validate_scripts.assert_called_once_with(False)


@patch("importlib.util.spec_from_file_location")
@patch("importlib.util.module_from_spec")
def test_validate_scripts_with_valid_scripts(
    mock_module_from_spec,
    mock_spec_from_file_location,
    mock_script_paths,
    mocker,
    capsys,
):
    """Tests validation of scripts with valid interface."""
    # Arrange
    repo_path, user_path = mock_script_paths

    script_file = Path("/mock/repo/voice_library_scripts/valid_script.py")

    directories = {repo_path, user_path}
    files = {script_file}

    def mock_is_dir(self):
        return self in directories

    def mock_is_file(self):
        return self in files

    def mock_iterdir(self):
        if self == repo_path:
            return [script_file]
        return []

    mocker.patch.object(Path, "is_dir", mock_is_dir)
    mocker.patch.object(Path, "is_file", mock_is_file)
    mocker.patch.object(Path, "iterdir", mock_iterdir)

    # Mock successful module loading
    mock_spec = MagicMock()
    mock_spec.loader = MagicMock()
    mock_spec_from_file_location.return_value = mock_spec

    mock_script_module = MagicMock()
    mock_script_module.get_argument_parser = MagicMock()
    mock_script_module.run = MagicMock()
    mock_module_from_spec.return_value = mock_script_module

    # Act
    is_valid = validate_scripts(project_only=False)

    # Assert
    assert is_valid is True


@patch("importlib.util.spec_from_file_location")
@patch("importlib.util.module_from_spec")
def test_validate_scripts_missing_get_argument_parser(
    mock_module_from_spec,
    mock_spec_from_file_location,
    mock_script_paths,
    mocker,
    capsys,
):
    """Tests validation of scripts missing get_argument_parser method."""
    # Arrange
    repo_path, user_path = mock_script_paths

    script_file = Path("/mock/repo/voice_library_scripts/invalid_script.py")

    directories = {repo_path, user_path}
    files = {script_file}

    def mock_is_dir(self):
        return self in directories

    def mock_is_file(self):
        return self in files

    def mock_iterdir(self):
        if self == repo_path:
            return [script_file]
        return []

    mocker.patch.object(Path, "is_dir", mock_is_dir)
    mocker.patch.object(Path, "is_file", mock_is_file)
    mocker.patch.object(Path, "iterdir", mock_iterdir)

    # Mock module loading with missing method
    mock_spec = MagicMock()
    mock_spec.loader = MagicMock()
    mock_spec_from_file_location.return_value = mock_spec

    mock_script_module = MagicMock()
    mock_script_module.run = MagicMock()
    del mock_script_module.get_argument_parser  # Missing method
    mock_module_from_spec.return_value = mock_script_module

    # Act
    is_valid = validate_scripts(project_only=False)

    # Assert
    assert is_valid is False
    captured = capsys.readouterr()
    assert "does not have get_argument_parser() and run() functions" in captured.out


@patch("importlib.util.spec_from_file_location")
@patch("importlib.util.module_from_spec")
def test_validate_scripts_missing_run_method(
    mock_module_from_spec,
    mock_spec_from_file_location,
    mock_script_paths,
    mocker,
    capsys,
):
    """Tests validation of scripts missing run method."""
    # Arrange
    repo_path, user_path = mock_script_paths

    script_file = Path("/mock/repo/voice_library_scripts/invalid_script.py")

    directories = {repo_path, user_path}
    files = {script_file}

    def mock_is_dir(self):
        return self in directories

    def mock_is_file(self):
        return self in files

    def mock_iterdir(self):
        if self == repo_path:
            return [script_file]
        return []

    mocker.patch.object(Path, "is_dir", mock_is_dir)
    mocker.patch.object(Path, "is_file", mock_is_file)
    mocker.patch.object(Path, "iterdir", mock_iterdir)

    # Mock module loading with missing method
    mock_spec = MagicMock()
    mock_spec.loader = MagicMock()
    mock_spec_from_file_location.return_value = mock_spec

    mock_script_module = MagicMock()
    mock_script_module.get_argument_parser = MagicMock()
    del mock_script_module.run  # Missing method
    mock_module_from_spec.return_value = mock_script_module

    # Act
    is_valid = validate_scripts(project_only=False)

    # Assert
    assert is_valid is False
    captured = capsys.readouterr()
    assert "does not have get_argument_parser() and run() functions" in captured.out


@patch("importlib.util.spec_from_file_location")
def test_validate_scripts_import_error(
    mock_spec_from_file_location, mock_script_paths, mocker, capsys
):
    """Tests validation of scripts with import errors."""
    # Arrange
    repo_path, user_path = mock_script_paths

    script_file = Path("/mock/repo/voice_library_scripts/broken_script.py")

    directories = {repo_path, user_path}
    files = {script_file}

    def mock_is_dir(self):
        return self in directories

    def mock_is_file(self):
        return self in files

    def mock_iterdir(self):
        if self == repo_path:
            return [script_file]
        return []

    mocker.patch.object(Path, "is_dir", mock_is_dir)
    mocker.patch.object(Path, "is_file", mock_is_file)
    mocker.patch.object(Path, "iterdir", mock_iterdir)

    # Mock import error
    mock_spec_from_file_location.return_value = None

    # Act
    is_valid = validate_scripts(project_only=False)

    # Assert
    assert is_valid is False
    captured = capsys.readouterr()
    assert "Error loading script" in captured.out


def test_validate_scripts_duplicate_names(mock_script_paths, mocker, capsys):
    """Tests validation with duplicate script names."""
    # Arrange
    repo_path, user_path = mock_script_paths

    repo_script = Path("/mock/repo/voice_library_scripts/duplicate.py")
    user_script = Path("/mock/user/voice_library/voice_library_scripts/duplicate.py")

    directories = {repo_path, user_path}
    files = {repo_script, user_script}

    def mock_is_dir(self):
        return self in directories

    def mock_is_file(self):
        return self in files

    def mock_iterdir(self):
        if self == repo_path:
            return [repo_script]
        elif self == user_path:
            return [user_script]
        return []

    mocker.patch.object(Path, "is_dir", mock_is_dir)
    mocker.patch.object(Path, "is_file", mock_is_file)
    mocker.patch.object(Path, "iterdir", mock_iterdir)

    # Act
    is_valid = validate_scripts(project_only=False)

    # Assert
    assert is_valid is False
    captured = capsys.readouterr()
    assert "Duplicate script name 'duplicate' found" in captured.out


@patch("importlib.util.spec_from_file_location")
@patch("importlib.util.module_from_spec")
def test_validate_scripts_mixed_valid_invalid(
    mock_module_from_spec,
    mock_spec_from_file_location,
    mock_script_paths,
    mocker,
    capsys,
):
    """Tests validation with mix of valid and invalid scripts."""
    # Arrange
    repo_path, user_path = mock_script_paths

    valid_script = Path("/mock/repo/voice_library_scripts/valid.py")
    invalid_script = Path("/mock/repo/voice_library_scripts/invalid.py")

    directories = {repo_path, user_path}
    files = {valid_script, invalid_script}

    def mock_is_dir(self):
        return self in directories

    def mock_is_file(self):
        return self in files

    def mock_iterdir(self):
        if self == repo_path:
            return [valid_script, invalid_script]
        return []

    mocker.patch.object(Path, "is_dir", mock_is_dir)
    mocker.patch.object(Path, "is_file", mock_is_file)
    mocker.patch.object(Path, "iterdir", mock_iterdir)

    # Mock different behaviors for each script
    def mock_spec_side_effect(name, path):
        if path == valid_script:
            mock_spec = MagicMock()
            mock_spec.loader = MagicMock()
            return mock_spec
        else:
            return None  # Import error for invalid script

    mock_spec_from_file_location.side_effect = mock_spec_side_effect

    # Mock valid module
    mock_script_module = MagicMock()
    mock_script_module.get_argument_parser = MagicMock()
    mock_script_module.run = MagicMock()
    mock_module_from_spec.return_value = mock_script_module

    # Act
    is_valid = validate_scripts(project_only=False)

    # Assert
    assert is_valid is False
    captured = capsys.readouterr()
    assert "Error loading script 'invalid'" in captured.out


def test_validate_scripts_project_only_flag(mock_script_paths, mocker):
    """Tests that project_only flag affects which directories are validated."""
    # Arrange
    repo_path, user_path = mock_script_paths

    directories = {repo_path, user_path}
    files = set()

    def mock_is_dir(self):
        return self in directories

    def mock_is_file(self):
        return self in files

    mocker.patch.object(Path, "is_dir", mock_is_dir)
    mocker.patch.object(Path, "iterdir", lambda self: [])

    # Act
    is_valid = validate_scripts(project_only=True)

    # Assert
    assert is_valid is True
