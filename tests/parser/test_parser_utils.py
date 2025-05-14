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

from script_to_speech.parser.utils.logging_utils import setup_parser_logging
from script_to_speech.parser.utils.text_utils import extract_text_preserving_whitespace
from script_to_speech.utils.file_system_utils import (
    sanitize_name,
)


class TestFileUtils:
    """Tests for file utility functions."""

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
