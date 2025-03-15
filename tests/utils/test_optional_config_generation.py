import os
from pathlib import Path
from unittest.mock import MagicMock, Mock, mock_open, patch

import pytest
import yaml

from utils.optional_config_generation import (
    create_default_config,
    generate_optional_config,
    get_optional_config_path,
    write_config_file,
)


class TestCreateDefaultConfig:
    """Tests for the create_default_config function."""

    def test_create_default_config(self):
        """Test that create_default_config returns the expected default configuration."""
        config = create_default_config()

        # Verify the structure of the default config
        assert isinstance(config, dict)
        assert "id3_tag_config" in config
        assert isinstance(config["id3_tag_config"], dict)

        # Verify the ID3 tag config has expected fields
        id3_config = config["id3_tag_config"]
        assert "title" in id3_config
        assert "screenplay_author" in id3_config
        assert "date" in id3_config

        # Verify all fields are empty strings
        assert id3_config["title"] == ""
        assert id3_config["screenplay_author"] == ""
        assert id3_config["date"] == ""


class TestWriteConfigFile:
    """Tests for the write_config_file function."""

    def test_write_config_file(self):
        """Test that write_config_file writes the config to a file."""
        # Create test config
        config = {"test_key": "test_value"}

        # Mock open for writing
        mock_file = mock_open()

        with patch("builtins.open", mock_file):
            # Call function
            write_config_file("/test/config_path.yaml", config)

            # Verify file was opened correctly
            mock_file.assert_called_once_with(
                "/test/config_path.yaml", "w", encoding="utf-8"
            )

            # Verify yaml.dump was called with the config
            file_handle = mock_file()
            assert file_handle.write.called

            # Unfortunately we can't easily test the exact yaml dump content
            # without mocking yaml.dump itself, but we can at least verify it was called


class TestGetOptionalConfigPath:
    """Tests for the get_optional_config_path function."""

    def test_get_optional_config_path(self):
        """Test that get_optional_config_path returns the expected path."""
        # Test with different path formats

        # Test with simple filename
        json_path = "test.json"
        config_path = get_optional_config_path(json_path)
        assert config_path == "test_optional_config.yaml"

        # Test with absolute path
        json_path = "/absolute/path/to/test.json"
        config_path = get_optional_config_path(json_path)
        expected_path = str(Path("/absolute/path/to/test_optional_config.yaml"))
        assert config_path == expected_path

        # Test with filename containing dots
        json_path = "test.something.json"
        config_path = get_optional_config_path(json_path)
        assert config_path == "test.something_optional_config.yaml"


class TestGenerateOptionalConfig:
    """Tests for the generate_optional_config function."""

    @patch("utils.optional_config_generation.os.path.exists")
    @patch("utils.optional_config_generation.write_config_file")
    def test_generate_optional_config_new_file(self, mock_write_config, mock_exists):
        """Test generate_optional_config when config file doesn't exist."""
        # Mock os.path.exists to return False (file doesn't exist)
        mock_exists.return_value = False

        # Call function
        config_path = generate_optional_config("test.json")

        # Verify get_optional_config_path was used
        expected_path = "test_optional_config.yaml"
        assert config_path == expected_path

        # Verify os.path.exists was called with the expected path
        mock_exists.assert_called_once_with(expected_path)

        # Verify write_config_file was called with expected arguments
        mock_write_config.assert_called_once()
        assert mock_write_config.call_args[0][0] == expected_path
        # The second argument should be the default config
        assert isinstance(mock_write_config.call_args[0][1], dict)
        assert "id3_tag_config" in mock_write_config.call_args[0][1]

    @patch("utils.optional_config_generation.os.path.exists")
    @patch("utils.optional_config_generation.write_config_file")
    def test_generate_optional_config_existing_file(
        self, mock_write_config, mock_exists
    ):
        """Test generate_optional_config when config file already exists."""
        # Mock os.path.exists to return True (file exists)
        mock_exists.return_value = True

        # Call function
        config_path = generate_optional_config("test.json")

        # Verify get_optional_config_path was used
        expected_path = "test_optional_config.yaml"
        assert config_path == expected_path

        # Verify os.path.exists was called with the expected path
        mock_exists.assert_called_once_with(expected_path)

        # Verify write_config_file was not called
        mock_write_config.assert_not_called()

    @patch("utils.optional_config_generation.os.path.exists")
    @patch("utils.optional_config_generation.create_default_config")
    @patch("utils.optional_config_generation.write_config_file")
    def test_generate_optional_config_integration(
        self, mock_write_config, mock_create_default, mock_exists
    ):
        """Test the integration of all functions in generate_optional_config."""
        # Mock os.path.exists to return False (file doesn't exist)
        mock_exists.return_value = False

        # Mock create_default_config to return a specific config
        test_config = {"test_key": "test_value"}
        mock_create_default.return_value = test_config

        # Call function
        config_path = generate_optional_config("/path/to/test.json")

        # Verify get_optional_config_path was used correctly
        expected_path = str(Path("/path/to/test_optional_config.yaml"))
        assert config_path == expected_path

        # Verify create_default_config was called
        mock_create_default.assert_called_once()

        # Verify write_config_file was called with expected arguments
        mock_write_config.assert_called_once_with(expected_path, test_config)
