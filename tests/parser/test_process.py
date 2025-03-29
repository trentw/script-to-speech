"""
Unit tests for the process module in the parser package.

This module focuses on testing the functionality for processing screenplay files
(PDF or TXT) to generate JSON chunks.
"""

import json
import os
from parser.process import main, process_screenplay
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest


class TestProcessScreenplay:
    """Tests for the process_screenplay function."""

    @patch("parser.process.extract_text_preserving_whitespace")
    @patch("parser.process.ScreenplayParser")
    @patch("parser.process.create_directory_structure")
    @patch("parser.process.create_output_folders")
    @patch("parser.process.setup_parser_logging")
    @patch("parser.process.generate_optional_config")
    @patch("shutil.copy2")
    @patch("os.path.exists")
    @patch("os.path.samefile")
    @patch("builtins.open", new_callable=mock_open)
    def test_process_pdf_file(
        self,
        mock_file_open,
        mock_samefile,
        mock_exists,
        mock_copy,
        mock_generate_config,
        mock_setup_logging,
        mock_create_folders,
        mock_create_structure,
        mock_parser,
        mock_extract_text,
    ):
        """Test processing a PDF file."""
        # Mock file existence
        mock_exists.return_value = True

        # Mock file comparison
        mock_samefile.return_value = False

        # Mock folder creation
        mock_create_folders.return_value = ("/path/to/screenplay", "/path/to/log")

        # Mock text extraction
        mock_extract_text.return_value = "Extracted text"

        # Mock parser
        mock_parser_instance = MagicMock()
        mock_parser_instance.parse_screenplay.return_value = [
            {"type": "title", "text": "Title"}
        ]
        mock_parser.return_value = mock_parser_instance

        # Mock config generation
        mock_generate_config.return_value = "/path/to/config"

        # Call function
        process_screenplay("test.pdf")

        # Check that directory structure was created
        mock_create_structure.assert_called_once()

        # Check that text was extracted
        mock_extract_text.assert_called_once()

        # Check that parser was called
        mock_parser.assert_called_once()
        mock_parser_instance.parse_screenplay.assert_called_once_with("Extracted text")

        # Check that JSON was written
        mock_file_open.assert_called()

        # Check that config was generated
        mock_generate_config.assert_called_once()

    @patch("parser.process.ScreenplayParser")
    @patch("parser.process.create_directory_structure")
    @patch("parser.process.create_output_folders")
    @patch("parser.process.setup_parser_logging")
    @patch("parser.process.generate_optional_config")
    @patch("shutil.copy2")
    @patch("os.path.exists")
    @patch("os.path.samefile")
    @patch("builtins.open", new_callable=mock_open)
    def test_process_txt_file(
        self,
        mock_file_open,
        mock_samefile,
        mock_exists,
        mock_copy,
        mock_generate_config,
        mock_setup_logging,
        mock_create_folders,
        mock_create_structure,
        mock_parser,
    ):
        """Test processing a TXT file."""
        # Mock file existence
        mock_exists.return_value = True

        # Mock file comparison
        mock_samefile.return_value = False

        # Mock folder creation
        mock_create_folders.return_value = ("/path/to/screenplay", "/path/to/log")

        # Set up mock file content
        mock_file_open.return_value.__enter__.return_value.read.return_value = (
            "Text file content"
        )

        # Mock parser
        mock_parser_instance = MagicMock()
        mock_parser_instance.parse_screenplay.return_value = [
            {"type": "title", "text": "Title"}
        ]
        mock_parser.return_value = mock_parser_instance

        # Mock config generation
        mock_generate_config.return_value = "/path/to/config"

        # Call function
        process_screenplay("test.txt")

        # Check that directory structure was created
        mock_create_structure.assert_called_once()

        # Check that text file was read
        mock_file_open.assert_called()

        # Check that parser was called
        mock_parser.assert_called_once()
        mock_parser_instance.parse_screenplay.assert_called_once_with(
            "Text file content"
        )

        # Check that config was generated
        mock_generate_config.assert_called_once()

    @patch("os.path.exists")
    def test_process_nonexistent_file(self, mock_exists):
        """Test processing a nonexistent file."""
        # Mock file existence
        mock_exists.return_value = False

        # Call function and check for exception
        with pytest.raises(FileNotFoundError):
            process_screenplay("nonexistent.pdf")

    @patch("os.path.exists")
    def test_process_unsupported_file_type(self, mock_exists):
        """Test processing an unsupported file type."""
        # Mock file existence
        mock_exists.return_value = True

        # Call function and check for exception
        with pytest.raises(ValueError):
            process_screenplay("test.doc")

    @patch("parser.process.process_screenplay")
    @patch("argparse.ArgumentParser.parse_args")
    def test_main_function(self, mock_parse_args, mock_process):
        """Test the main function."""
        # Mock command line arguments
        mock_args = MagicMock()
        mock_args.input_file = "test.pdf"
        mock_args.output_dir = None
        mock_args.text_only = False
        mock_parse_args.return_value = mock_args

        # Call function
        main()

        # Check that process_screenplay was called with correct arguments
        mock_process.assert_called_once_with("test.pdf", None, False)

    @patch("parser.process.process_screenplay")
    @patch("argparse.ArgumentParser.parse_args")
    def test_main_function_with_error(self, mock_parse_args, mock_process):
        """Test the main function with an error."""
        # Mock command line arguments
        mock_args = MagicMock()
        mock_args.input_file = "test.pdf"
        mock_args.output_dir = None
        mock_args.text_only = False
        mock_parse_args.return_value = mock_args

        # Mock process_screenplay to raise an exception
        mock_process.side_effect = Exception("Test error")

        # Call function
        with pytest.raises(SystemExit):
            main()
