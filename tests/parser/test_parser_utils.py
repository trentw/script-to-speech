"""
Unit tests for the utility functions in the parser module.

This module focuses on testing the utility functions in the parser/utils directory,
including file handling, text processing, and logging utilities.
"""

import os
import tempfile
from parser.utils.file_utils import (
    create_directory_structure,
    create_output_folders,
    get_project_root,
    sanitize_name,
)
from parser.utils.logging_utils import setup_parser_logging
from parser.utils.text_utils import extract_text_preserving_whitespace
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest


class TestFileUtils:
    """Tests for file utility functions."""

    def test_get_project_root(self):
        """Test getting project root directory."""
        # The function should return a Path object
        root = get_project_root()
        assert isinstance(root, Path)

        # The path should exist
        assert root.exists()

        # The path should contain expected directories
        assert (root / "parser").exists()
        assert (root / "tests").exists()

    def test_sanitize_name(self):
        """Test sanitizing names for use in filenames."""
        # Test basic sanitization
        assert sanitize_name("test name") == "test_name"

        # Test with special characters
        assert sanitize_name("test@name!") == "testname"

        # Test with multiple spaces and dashes
        assert sanitize_name("test  -  name") == "test_name"

        # Test with leading/trailing spaces and underscores
        assert sanitize_name("  _test name_  ") == "test_name"

        # Test with empty string
        assert sanitize_name("") == ""

    def test_create_directory_structure(self):
        """Test creating directory structure."""
        # Create a patch for the mkdir method
        with patch.object(Path, "mkdir") as mock_mkdir:
            # Call function
            create_directory_structure()

            # Check that mkdir was called at least twice (once for each directory)
            assert mock_mkdir.call_count >= 2
            mock_mkdir.assert_called_with(parents=True, exist_ok=True)

    def test_create_output_folders(self):
        """Test creating output folders."""
        # Use a simpler approach with a direct mock of the function
        with patch("parser.utils.file_utils.get_project_root") as mock_get_root:
            # Create mock paths
            mock_root = MagicMock()
            mock_get_root.return_value = mock_root

            # Create mock for the screenplay directory
            mock_screenplay_dir = MagicMock()
            mock_screenplay_dir.__str__.return_value = "/mock/path/to/screenplay"

            # Create mock for the log file
            mock_log_file = MagicMock()
            mock_log_file.__str__.return_value = "/mock/path/to/log.log"

            # Set up the path structure
            mock_input = MagicMock()
            mock_parser = MagicMock()
            mock_logs = MagicMock()

            # Configure __truediv__ to return our mocks
            mock_root.__truediv__.side_effect = lambda x: (
                mock_input if x == "input" else mock_parser
            )
            mock_input.__truediv__.return_value = mock_screenplay_dir
            mock_parser.__truediv__.side_effect = lambda x: (
                mock_logs if x == "logs" else MagicMock()
            )
            mock_logs.__truediv__.return_value = mock_log_file

            # Call the function
            screenplay_dir, log_file = create_output_folders(
                "test_screenplay", "test_mode"
            )

            # Verify the mkdir was called on the screenplay directory
            mock_screenplay_dir.mkdir.assert_called_once_with(
                parents=True, exist_ok=True
            )

            # Check return values
            assert screenplay_dir == "/mock/path/to/screenplay"
            assert log_file == "/mock/path/to/log.log"


class TestTextUtils:
    """Tests for text utility functions."""

    @patch("pdfplumber.open")
    @patch("builtins.open", new_callable=mock_open)
    def test_extract_text_preserving_whitespace(self, mock_file_open, mock_pdf_open):
        """Test extracting text from PDF while preserving whitespace."""
        # Mock PDF pages
        mock_page1 = MagicMock()
        mock_page1.dedupe_chars.return_value = mock_page1
        mock_page1.extract_text.return_value = "Page 1 text\nwith multiple lines"

        mock_page2 = MagicMock()
        mock_page2.dedupe_chars.return_value = mock_page2
        mock_page2.extract_text.return_value = "Page 2 text\nwith more lines"

        # Set up mock PDF object
        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page1, mock_page2]
        mock_pdf_open.return_value.__enter__.return_value = mock_pdf

        # Call function
        result = extract_text_preserving_whitespace("test.pdf", "output.txt")

        # Check that PDF was opened
        mock_pdf_open.assert_called_once_with("test.pdf")

        # Check that extract_text was called with correct parameters
        mock_page1.extract_text.assert_called_once_with(
            x_tolerance=1, y_tolerance=1, layout=True
        )
        mock_page2.extract_text.assert_called_once_with(
            x_tolerance=1, y_tolerance=1, layout=True
        )

        # Check that output file was written
        mock_file_open.assert_called_once_with("output.txt", "w", encoding="utf-8")
        mock_file_open().write.assert_called_once_with(
            "Page 1 text\nwith multiple linesPage 2 text\nwith more lines"
        )

        # Check return value
        assert result == "Page 1 text\nwith multiple linesPage 2 text\nwith more lines"


class TestLoggingUtils:
    """Tests for logging utility functions."""

    @patch("parser.utils.logging_utils.setup_screenplay_logging")
    @patch("pathlib.Path.mkdir")
    def test_setup_parser_logging(self, mock_mkdir, mock_setup_logging):
        """Test setting up parser logging."""
        # Call function
        setup_parser_logging("test.log", file_level=10, console_level=20)

        # Check that directory was created
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

        # Check that setup_screenplay_logging was called with correct parameters
        mock_setup_logging.assert_called_once_with("test.log", 10, 20)


class TestIntegrationTests:
    """Integration tests for utility functions."""

    @pytest.mark.integration
    def test_file_utils_integration(self):
        """Integration test for file utility functions."""
        # Create a temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test sanitize_name
            sanitized = sanitize_name("test@name!")
            assert sanitized == "testname"

            # Create a file with the sanitized name
            file_path = os.path.join(temp_dir, f"{sanitized}.txt")
            with open(file_path, "w") as f:
                f.write("Test content")

            # Check that the file exists
            assert os.path.exists(file_path)

            # Read the file content
            with open(file_path, "r") as f:
                content = f.read()

            # Check the content
            assert content == "Test content"
