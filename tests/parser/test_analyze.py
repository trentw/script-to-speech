"""
Unit tests for the analyze module in the parser package.

This module focuses on testing the functionality for analyzing screenplay JSON chunks
and generating statistics.
"""

import json
from parser.analyze import analyze_chunks, analyze_screenplay_chunks, main
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest


class TestAnalyzeChunks:
    """Tests for the analyze_chunks function."""

    @patch("parser.analyze.logger")
    def test_analyze_empty_chunks(self, mock_logger):
        """Test analyzing empty chunks list."""
        # Call function
        analyze_chunks([])

        # Check that logger was called with expected messages
        mock_logger.info.assert_any_call("\nChunk Type Counts:")
        mock_logger.info.assert_any_call(f"\nTotal Distinct Speakers:\n  {0}")
        mock_logger.info.assert_any_call("\nSpeaker Line Counts:")

    @patch("parser.analyze.logger")
    def test_analyze_basic_chunks(self, mock_logger):
        """Test analyzing basic chunks."""
        # Create test chunks
        chunks = [
            {"type": "title", "text": "Title"},
            {"type": "scene_heading", "text": "INT. LIVING ROOM - DAY"},
            {"type": "action", "text": "John enters the room."},
        ]

        # Call function
        analyze_chunks(chunks)

        # Check that logger was called with expected messages
        mock_logger.info.assert_any_call("\nChunk Type Counts:")
        mock_logger.info.assert_any_call("  title: 1")
        mock_logger.info.assert_any_call("  scene_heading: 1")
        mock_logger.info.assert_any_call("  action: 1")
        mock_logger.info.assert_any_call(
            f"\nTotal Distinct Speakers:\n  {1}"
        )  # Default speaker
        mock_logger.info.assert_any_call("\nSpeaker Line Counts:")
        mock_logger.info.assert_any_call("  (default): 3")

    @patch("parser.analyze.logger")
    def test_analyze_chunks_with_dialog(self, mock_logger):
        """Test analyzing chunks with dialog."""
        # Create test chunks
        chunks = [
            {"type": "scene_heading", "text": "INT. LIVING ROOM - DAY"},
            {"type": "action", "text": "John enters the room."},
            {"type": "speaker_attribution", "speaker": "", "text": "JOHN"},
            {"type": "dialog", "speaker": "JOHN", "text": "Hello, how are you?"},
            {"type": "speaker_attribution", "speaker": "", "text": "MARY"},
            {"type": "dialog", "speaker": "MARY", "text": "I'm fine, thank you."},
        ]

        # Call function
        analyze_chunks(chunks)

        # Check that logger was called with expected messages
        mock_logger.info.assert_any_call("\nChunk Type Counts:")
        mock_logger.info.assert_any_call("  scene_heading: 1")
        mock_logger.info.assert_any_call("  action: 1")
        mock_logger.info.assert_any_call("  speaker_attribution: 2")
        mock_logger.info.assert_any_call("  dialog: 2")
        mock_logger.info.assert_any_call(
            f"\nTotal Distinct Speakers:\n  {3}"
        )  # JOHN, MARY, default
        mock_logger.info.assert_any_call("\nSpeaker Line Counts:")
        # Check for speaker counts (order may vary due to sorting)
        assert any(
            "  JOHN: 1" in call.args[0] for call in mock_logger.info.call_args_list
        )
        assert any(
            "  MARY: 1" in call.args[0] for call in mock_logger.info.call_args_list
        )
        assert any(
            "  (default): 4" in call.args[0] for call in mock_logger.info.call_args_list
        )


class TestAnalyzeScreenplayChunks:
    """Tests for the analyze_screenplay_chunks function."""

    @patch("parser.analyze.analyze_chunks")
    @patch("parser.analyze.setup_parser_logging")
    @patch("parser.analyze.sanitize_name")
    @patch("datetime.datetime")
    @patch("pathlib.Path.mkdir")
    @patch("builtins.open", new_callable=mock_open)
    def test_analyze_screenplay_chunks(
        self,
        mock_file_open,
        mock_mkdir,
        mock_datetime,
        mock_sanitize,
        mock_setup_logging,
        mock_analyze,
    ):
        """Test analyzing screenplay chunks from a JSON file."""
        # Mock datetime
        mock_datetime.now.return_value.strftime.return_value = "20250323_123456"

        # Mock sanitize_name
        mock_sanitize.return_value = "test_screenplay"

        # Set up mock file content
        mock_file_open.return_value.__enter__.return_value.read.return_value = (
            json.dumps(
                [
                    {"type": "title", "text": "Title"},
                    {"type": "scene_heading", "text": "INT. LIVING ROOM - DAY"},
                ]
            )
        )

        # Call function
        analyze_screenplay_chunks("test_screenplay.json")

        # Check that logging was set up
        mock_setup_logging.assert_called_once()

        # Check that file was opened
        mock_file_open.assert_called_with("test_screenplay.json", "r", encoding="utf-8")

        # Check that analyze_chunks was called
        mock_analyze.assert_called_once()
        assert len(mock_analyze.call_args[0][0]) == 2  # Should have 2 chunks

    @patch("parser.analyze.analyze_screenplay_chunks")
    @patch("argparse.ArgumentParser.parse_args")
    def test_main_function(self, mock_parse_args, mock_analyze):
        """Test the main function."""
        # Mock command line arguments
        mock_args = MagicMock()
        mock_args.json_file = "test_screenplay.json"
        mock_parse_args.return_value = mock_args

        # Call function
        main()

        # Check that analyze_screenplay_chunks was called with correct arguments
        mock_analyze.assert_called_once_with("test_screenplay.json")

    @patch("parser.analyze.analyze_screenplay_chunks")
    @patch("argparse.ArgumentParser.parse_args")
    def test_main_function_with_error(self, mock_parse_args, mock_analyze):
        """Test the main function with an error."""
        # Mock command line arguments
        mock_args = MagicMock()
        mock_args.json_file = "test_screenplay.json"
        mock_parse_args.return_value = mock_args

        # Mock analyze_screenplay_chunks to raise an exception
        mock_analyze.side_effect = Exception("Test error")

        # Call function
        with pytest.raises(SystemExit):
            main()
