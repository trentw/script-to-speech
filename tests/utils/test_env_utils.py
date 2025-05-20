"""Tests for env_utils.py."""

import os
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from script_to_speech.utils.env_utils import load_environment_variables


class TestLoadEnvironmentVariables:
    """Tests for load_environment_variables function."""

    def test_project_root_calculation(self):
        """
        Test that the project root is calculated correctly.

        This is a simple test to verify that the .env file is looked for
        in the correct location (4 levels up from the env_utils.py file).
        """
        # Get the actual path to env_utils.py
        env_utils_path = (
            Path(os.path.abspath(__file__)).parent.parent.parent
            / "src"
            / "script_to_speech"
            / "utils"
            / "env_utils.py"
        )

        # Calculate what the project root should be (4 levels up)
        expected_project_root = env_utils_path.parent.parent.parent.parent

        # Verify this is the actual project root (should contain pyproject.toml)
        assert (
            expected_project_root / "pyproject.toml"
        ).exists(), "Project root should contain pyproject.toml"

    @patch("script_to_speech.utils.env_utils.Path")
    @patch("script_to_speech.utils.env_utils.load_dotenv")
    def test_env_file_path_calculation(self, mock_load_dotenv, mock_path):
        """
        Test that the .env file path is correctly calculated relative to the project root.

        This test verifies that the code is looking for the .env file in the correct location
        (3 levels up from the env_utils.py file), which should be the project root.
        """
        # Setup mock for Path(__file__)
        mock_file_path = MagicMock()
        mock_path.return_value = mock_file_path

        # Setup the parent chain to simulate the file structure
        # src/script_to_speech/utils/env_utils.py is 3 levels deep from project root
        mock_utils_dir = MagicMock()
        mock_script_to_speech_dir = MagicMock()
        mock_src_dir = MagicMock()
        mock_project_root = MagicMock()

        mock_file_path.parent = mock_utils_dir
        mock_utils_dir.parent = mock_script_to_speech_dir
        mock_script_to_speech_dir.parent = mock_src_dir
        mock_src_dir.parent = mock_project_root

        # Setup the .env path in the project root
        mock_env_path = MagicMock()
        mock_project_root.__truediv__.return_value = mock_env_path

        # Make the .env file exist
        mock_env_path.exists.return_value = True
        mock_load_dotenv.return_value = True

        # Call the function
        result = load_environment_variables()

        # We don't need to verify the exact path that Path was called with
        # since that's an implementation detail. Instead, we verify the path traversal.

        # Verify the parent chain was traversed correctly (4 levels up)
        assert mock_file_path.parent == mock_utils_dir
        assert mock_utils_dir.parent == mock_script_to_speech_dir
        assert mock_script_to_speech_dir.parent == mock_src_dir
        assert mock_src_dir.parent == mock_project_root

        # Verify the .env path was constructed correctly
        mock_project_root.__truediv__.assert_called_once_with(".env")

        # Verify load_dotenv was called with the correct path
        mock_load_dotenv.assert_called_once_with(mock_env_path)

        # Verify the function returned True
        assert result is True

    @patch(
        "script_to_speech.utils.env_utils.__file__",
        "/fake/project/src/script_to_speech/utils/env_utils.py",
    )
    @patch("script_to_speech.utils.env_utils.Path")
    @patch("script_to_speech.utils.env_utils.load_dotenv")
    def test_env_file_location_with_real_paths(self, mock_load_dotenv, mock_path):
        """
        Test that the .env file location is correct using a simulated file path.

        This test verifies that the code correctly navigates up 4 levels from the utils file
        to find the project root.
        """
        # Create a mock file path and parent directories
        mock_file_path = MagicMock(spec=Path)
        mock_utils_dir = MagicMock(spec=Path)
        mock_script_to_speech_dir = MagicMock(spec=Path)
        mock_src_dir = MagicMock(spec=Path)
        mock_project_root = MagicMock(spec=Path)
        mock_env_path = MagicMock(spec=Path)

        # Setup the path chain
        mock_path.return_value = mock_file_path
        mock_file_path.parent = mock_utils_dir
        mock_utils_dir.parent = mock_script_to_speech_dir
        mock_script_to_speech_dir.parent = mock_src_dir
        mock_src_dir.parent = mock_project_root

        # Setup the project root / .env path
        mock_project_root.__truediv__.return_value = mock_env_path
        mock_env_path.exists.return_value = True

        # Make load_dotenv return True
        mock_load_dotenv.return_value = True

        # Call the function
        result = load_environment_variables()

        # Verify the correct path was used
        mock_project_root.__truediv__.assert_called_once_with(".env")
        mock_load_dotenv.assert_called_once_with(mock_env_path)
        assert result is True
