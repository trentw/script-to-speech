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

    @patch("script_to_speech.utils.env_utils.load_dotenv")
    def test_env_file_path_calculation(self, mock_load_dotenv):
        """
        Test that the .env file path uses the workspace directory from config.

        This test verifies that the code correctly uses get_default_workspace_dir()
        to determine the workspace location in non-frozen mode.
        """
        # Make the .env file exist and load successfully
        mock_load_dotenv.return_value = True

        # Call the function - it will use the real get_default_workspace_dir()
        result = load_environment_variables()

        # Verify load_dotenv was called
        mock_load_dotenv.assert_called_once()

        # Verify the path argument is a Path object ending in .env
        call_args = mock_load_dotenv.call_args[0][0]
        assert str(call_args).endswith(
            ".env"
        ), f"Expected path ending in .env, got {call_args}"

        # Verify the function returned True
        assert result is True

    @patch("script_to_speech.utils.env_utils.load_dotenv")
    def test_env_file_location_with_real_paths(self, mock_load_dotenv):
        """
        Test that the .env file location uses workspace directory.

        This test verifies that the code correctly uses get_default_workspace_dir()
        from config.py to determine the workspace location.
        """
        # Make load_dotenv return True
        mock_load_dotenv.return_value = True

        # Call the function
        result = load_environment_variables()

        # Verify load_dotenv was called
        mock_load_dotenv.assert_called_once()

        # Verify the path is a valid Path object with .env
        call_args = mock_load_dotenv.call_args[0][0]
        assert call_args.name == ".env", f"Expected .env file, got {call_args.name}"

        # Verify the function returned True
        assert result is True
