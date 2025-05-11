"""
Unit tests for the utility functions in the parser module.

This module focuses on testing the utility functions in the parser/utils directory,
including file handling, text processing, and logging utilities.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

from script_to_speech.parser.utils.file_utils import (
    create_directory_structure,
    create_output_folders,
    get_project_root,
    sanitize_name,
)
from script_to_speech.parser.utils.logging_utils import setup_parser_logging
from script_to_speech.parser.utils.text_utils import extract_text_preserving_whitespace


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
        assert (root / "output").exists()
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

    @patch("script_to_speech.parser.utils.file_utils.get_project_root")
    # Removed patch for Path.mkdir as we will check calls on the mock path objects directly
    def test_create_directory_structure(self, mock_get_root):
        """Test creating the correct directory structure."""
        # Setup mock project root
        mock_root = MagicMock(spec=Path)
        mock_get_root.return_value = mock_root

        # Define expected paths relative to the mock root
        expected_input_path = mock_root / "input"
        expected_output_path = mock_root / "output"
        expected_logs_path = expected_output_path / "parser_logs"

        # Mock the path division to return specific mocks for assertion
        def truediv_side_effect(part):
            if part == "input":
                return expected_input_path
            elif part == "output":
                return expected_output_path
            else:
                # Default mock for any other division
                return MagicMock(spec=Path)

        mock_root.__truediv__.side_effect = truediv_side_effect
        expected_output_path.__truediv__.side_effect = lambda part: (
            expected_logs_path if part == "parser_logs" else MagicMock(spec=Path)
        )

        # Call the function
        create_directory_structure()

        # Assert that get_project_root was called
        mock_get_root.assert_called_once()

        # Assert that mkdir was called on the specific mock path objects
        expected_input_path.mkdir.assert_called_once_with(parents=True, exist_ok=True)
        expected_logs_path.mkdir.assert_called_once_with(parents=True, exist_ok=True)

    def test_create_output_folders(self):
        """Test creating output folders."""
        # Use a simpler approach with a direct mock of the function
        with patch(
            "script_to_speech.parser.utils.file_utils.get_project_root"
        ) as mock_get_root:
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
            mock_input = MagicMock(name="input_dir")
            mock_output = MagicMock(name="output_dir")
            mock_parser_logs = MagicMock(name="parser_logs_dir")

            # Configure __truediv__ to return our mocks reflecting new structure
            def root_truediv(part):
                if part == "input":
                    return mock_input
                elif part == "output":
                    return mock_output
                else:
                    return MagicMock(name=f"root_other_{part}")

            mock_root.__truediv__.side_effect = root_truediv

            mock_input.__truediv__.return_value = (
                mock_screenplay_dir  # input / screenplay_name
            )

            def output_truediv(part):
                if part == "parser_logs":
                    return mock_parser_logs
                else:
                    return MagicMock(name=f"output_other_{part}")

            mock_output.__truediv__.side_effect = output_truediv

            mock_parser_logs.__truediv__.return_value = (
                mock_log_file  # output / parser_logs / log_file_name
            )

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

    @patch("script_to_speech.parser.utils.logging_utils.setup_screenplay_logging")
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
