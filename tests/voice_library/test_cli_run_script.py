"""Tests for the voice library script runner CLI."""

import argparse
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from script_to_speech.voice_library.cli_run_script import find_scripts, main


@pytest.fixture
def mock_script_paths(mocker):
    """Mocks the script paths and filesystem for script discovery."""
    mock_repo_path = Path("/mock/repo/voice_library_scripts")
    mock_user_path = Path("/mock/user/voice_library/voice_library_scripts")

    mocker.patch(
        "script_to_speech.voice_library.cli_run_script.REPO_VOICE_LIBRARY_SCRIPTS_PATH",
        mock_repo_path,
    )
    mocker.patch(
        "script_to_speech.voice_library.cli_run_script.USER_VOICE_LIBRARY_SCRIPTS_PATH",
        mock_user_path,
    )

    return mock_repo_path, mock_user_path


def test_find_scripts_basic_functionality(mock_script_paths, mocker):
    """Tests basic script discovery functionality."""
    # Arrange
    repo_path, user_path = mock_script_paths

    # Use simple return values for easier testing
    mocker.patch("pathlib.Path.is_dir", return_value=True)
    mocker.patch("pathlib.Path.iterdir", return_value=[])

    # Act
    scripts = find_scripts()

    # Assert
    assert scripts == {}


def test_find_scripts_empty_directories(mock_script_paths, mocker):
    """Tests script discovery with empty directories."""
    # Arrange
    repo_path, user_path = mock_script_paths

    mocker.patch("pathlib.Path.is_dir", return_value=True)
    mocker.patch("pathlib.Path.iterdir", return_value=[])

    # Act
    scripts = find_scripts()

    # Assert
    assert scripts == {}


def test_find_scripts_nonexistent_directories(mock_script_paths, mocker):
    """Tests script discovery with non-existent directories."""
    # Arrange
    repo_path, user_path = mock_script_paths

    mocker.patch("pathlib.Path.is_dir", return_value=False)

    # Act
    scripts = find_scripts()

    # Assert
    assert scripts == {}


def test_find_scripts_mixed_file_structures(mock_script_paths, mocker):
    """Tests script discovery with mixed file structures."""
    # Arrange
    repo_path, user_path = mock_script_paths

    # Mock repo directory with both directory and file scripts
    repo_script_dir = Path("/mock/repo/voice_library_scripts/dir_script")
    repo_script_file = Path("/mock/repo/voice_library_scripts/file_script.py")

    # Create a mapping for which paths are directories vs files
    directories = {repo_path, user_path, repo_script_dir}
    files = {repo_script_file, repo_script_dir / "dir_script.py"}

    # Mock the path methods with proper instance handling
    original_is_dir = Path.is_dir
    original_is_file = Path.is_file
    original_iterdir = Path.iterdir

    def mock_is_dir(self):
        return self in directories

    def mock_is_file(self):
        return self in files

    def mock_iterdir(self):
        if self == repo_path:
            return [repo_script_dir, repo_script_file]
        elif self == user_path:
            return []
        return []

    mocker.patch.object(Path, "is_dir", mock_is_dir)
    mocker.patch.object(Path, "is_file", mock_is_file)
    mocker.patch.object(Path, "iterdir", mock_iterdir)

    # Act
    scripts = find_scripts()

    # Assert
    assert scripts == {
        "dir_script": repo_script_dir / "dir_script.py",
        "file_script": repo_script_file,
    }


def test_find_scripts_user_overrides_repo(mock_script_paths, mocker):
    """Tests that user scripts override repo scripts with same names."""
    # Arrange
    repo_path, user_path = mock_script_paths

    # Mock both directories having scripts with same name
    repo_script_file = Path("/mock/repo/voice_library_scripts/same_name.py")
    user_script_file = Path(
        "/mock/user/voice_library/voice_library_scripts/same_name.py"
    )

    directories = {repo_path, user_path}
    files = {repo_script_file, user_script_file}

    def mock_is_dir(self):
        return self in directories

    def mock_is_file(self):
        return self in files

    def mock_iterdir(self):
        if self == repo_path:
            return [repo_script_file]
        elif self == user_path:
            return [user_script_file]
        return []

    mocker.patch.object(Path, "is_dir", mock_is_dir)
    mocker.patch.object(Path, "is_file", mock_is_file)
    mocker.patch.object(Path, "iterdir", mock_iterdir)

    # Act
    scripts = find_scripts()

    # Assert
    assert scripts == {"same_name": user_script_file}


def test_find_scripts_directory_style_scripts(mock_script_paths, mocker):
    """Tests discovery of directory-style scripts (script_name/script_name.py)."""
    # Arrange
    repo_path, user_path = mock_script_paths

    script_dir = Path("/mock/repo/voice_library_scripts/complex_script")
    script_file = script_dir / "complex_script.py"

    directories = {repo_path, user_path, script_dir}
    files = {script_file}

    def mock_is_dir(self):
        return self in directories

    def mock_is_file(self):
        return self in files

    def mock_iterdir(self):
        if self == repo_path:
            return [script_dir]
        elif self == user_path:
            return []
        return []

    mocker.patch.object(Path, "is_dir", mock_is_dir)
    mocker.patch.object(Path, "is_file", mock_is_file)
    mocker.patch.object(Path, "iterdir", mock_iterdir)

    # Act
    scripts = find_scripts()

    # Assert
    assert scripts == {"complex_script": script_file}


def test_find_scripts_standalone_files_only(mock_script_paths, mocker):
    """Tests discovery of standalone Python files only."""
    # Arrange
    repo_path, user_path = mock_script_paths

    script1 = Path("/mock/repo/voice_library_scripts/script1.py")
    script2 = Path("/mock/repo/voice_library_scripts/script2.py")

    directories = {repo_path, user_path}
    files = {script1, script2}

    def mock_is_dir(self):
        return self in directories

    def mock_is_file(self):
        return self in files

    def mock_iterdir(self):
        if self == repo_path:
            return [script1, script2]
        elif self == user_path:
            return []
        return []

    mocker.patch.object(Path, "is_dir", mock_is_dir)
    mocker.patch.object(Path, "is_file", mock_is_file)
    mocker.patch.object(Path, "iterdir", mock_iterdir)

    # Act
    scripts = find_scripts()

    # Assert
    assert scripts == {"script1": script1, "script2": script2}


@patch("sys.argv", ["sts-voice-library-run-script", "test_script", "--param", "value"])
@patch("script_to_speech.voice_library.cli_run_script.find_scripts")
@patch("importlib.util.spec_from_file_location")
@patch("importlib.util.module_from_spec")
def test_main_success(
    mock_module_from_spec,
    mock_spec_from_file_location,
    mock_find_scripts,
):
    """Tests the successful execution of a script."""
    # Arrange
    mock_find_scripts.return_value = {"test_script": Path("/mock/test_script.py")}

    mock_spec = MagicMock()
    mock_spec.loader = MagicMock()
    mock_spec_from_file_location.return_value = mock_spec

    mock_script_module = MagicMock()
    mock_parser = MagicMock()
    mock_script_module.get_argument_parser.return_value = mock_parser
    mock_module_from_spec.return_value = mock_script_module

    # Act
    result = main()

    # Assert
    assert result == 0
    mock_script_module.get_argument_parser.assert_called_once()
    mock_parser.parse_args.assert_called_once_with(["--param", "value"])
    mock_script_module.run.assert_called_once()


@patch("sys.argv", ["sts-voice-library-run-script"])
@patch("script_to_speech.voice_library.cli_run_script.find_scripts")
def test_main_no_arguments(mock_find_scripts, capsys):
    """Tests that main() shows help when no arguments provided."""
    # Arrange
    mock_find_scripts.return_value = {"test_script": Path("/mock/test_script.py")}

    # Act
    result = main()

    # Assert
    assert result == 1
    captured = capsys.readouterr()
    assert "usage:" in captured.out


@patch("sys.argv", ["sts-voice-library-run-script", "nonexistent_script"])
@patch("script_to_speech.voice_library.cli_run_script.find_scripts")
def test_main_nonexistent_script(mock_find_scripts, capsys):
    """Tests that main() shows help when script doesn't exist."""
    # Arrange
    mock_find_scripts.return_value = {"test_script": Path("/mock/test_script.py")}

    # Act
    result = main()

    # Assert
    assert result == 1
    captured = capsys.readouterr()
    assert "usage:" in captured.out


@patch("sys.argv", ["sts-voice-library-run-script", "bad_script"])
@patch("script_to_speech.voice_library.cli_run_script.find_scripts")
@patch("importlib.util.spec_from_file_location")
@patch("importlib.util.module_from_spec")
def test_main_script_no_interface(
    mock_module_from_spec,
    mock_spec_from_file_location,
    mock_find_scripts,
):
    """Tests that main() fails if the script doesn't have the right functions."""
    # Arrange
    mock_find_scripts.return_value = {"bad_script": Path("/mock/bad_script.py")}

    mock_spec = MagicMock()
    mock_spec.loader = MagicMock()
    mock_spec_from_file_location.return_value = mock_spec

    mock_script_module = MagicMock()
    del mock_script_module.run  # Remove the run method
    mock_module_from_spec.return_value = mock_script_module

    # Act
    result = main()

    # Assert
    assert result == 1


@patch("sys.argv", ["sts-voice-library-run-script", "import_error_script"])
@patch("script_to_speech.voice_library.cli_run_script.find_scripts")
@patch("importlib.util.spec_from_file_location")
def test_main_import_error(
    mock_spec_from_file_location,
    mock_find_scripts,
    capsys,
):
    """Tests that main() handles ImportError gracefully."""
    # Arrange
    mock_find_scripts.return_value = {
        "import_error_script": Path("/mock/import_error_script.py")
    }
    mock_spec_from_file_location.return_value = None  # Simulate ImportError

    # Act
    result = main()

    # Assert
    assert result == 1
    captured = capsys.readouterr()
    assert "Error running script" in captured.out


@patch("sys.argv", ["sts-voice-library-run-script", "exception_script"])
@patch("script_to_speech.voice_library.cli_run_script.find_scripts")
@patch("importlib.util.spec_from_file_location")
@patch("importlib.util.module_from_spec")
def test_main_execution_exception(
    mock_module_from_spec,
    mock_spec_from_file_location,
    mock_find_scripts,
    capsys,
):
    """Tests that main() handles exceptions during script execution."""
    # Arrange
    mock_find_scripts.return_value = {
        "exception_script": Path("/mock/exception_script.py")
    }

    mock_spec = MagicMock()
    mock_spec.loader = MagicMock()
    mock_spec_from_file_location.return_value = mock_spec

    mock_script_module = MagicMock()
    mock_script_module.run.side_effect = Exception("Script execution failed")
    mock_module_from_spec.return_value = mock_script_module

    # Act
    result = main()

    # Assert
    assert result == 1
    captured = capsys.readouterr()
    assert "Error running script" in captured.out
    assert "Script execution failed" in captured.out


@patch("sys.argv", ["sts-voice-library-run-script", "missing_methods_script"])
@patch("script_to_speech.voice_library.cli_run_script.find_scripts")
@patch("importlib.util.spec_from_file_location")
@patch("importlib.util.module_from_spec")
def test_main_script_missing_get_argument_parser(
    mock_module_from_spec,
    mock_spec_from_file_location,
    mock_find_scripts,
    capsys,
):
    """Tests that main() fails if the script doesn't have get_argument_parser."""
    # Arrange
    mock_find_scripts.return_value = {
        "missing_methods_script": Path("/mock/missing_methods_script.py")
    }

    mock_spec = MagicMock()
    mock_spec.loader = MagicMock()
    mock_spec_from_file_location.return_value = mock_spec

    mock_script_module = MagicMock()
    del mock_script_module.get_argument_parser  # Remove the get_argument_parser method
    mock_module_from_spec.return_value = mock_script_module

    # Act
    result = main()

    # Assert
    assert result == 1
    captured = capsys.readouterr()
    assert "does not conform to the required interface" in captured.out
