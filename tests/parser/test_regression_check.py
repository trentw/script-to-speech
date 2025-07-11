"""
Unit tests for the regression_check module in the parser package.

This module focuses on testing the functionality for comparing parser output
with existing JSON files to detect regressions.
"""

import json
import logging
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

from script_to_speech.parser.regression_check import (
    analyze_chunks,
    compare_chunks_by_type,
    load_json_chunks,
    main,
    run_regression_check,
)


class TestLoadJsonChunks:
    """Tests for the load_json_chunks function."""

    @patch("builtins.open", new_callable=mock_open)
    def test_load_json_chunks(self, mock_file_open):
        """Test loading JSON chunks from a file."""
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
        chunks = load_json_chunks("test.json")

        # Check that file was opened
        mock_file_open.assert_called_once_with("test.json", "r", encoding="utf-8")

        # Check result
        assert len(chunks) == 2
        assert chunks[0]["type"] == "title"
        assert chunks[1]["type"] == "scene_heading"

    @patch("builtins.open", new_callable=mock_open)
    def test_load_json_chunks_error(self, mock_file_open):
        """Test error handling when loading JSON chunks."""
        # Mock open to raise an exception
        mock_file_open.side_effect = Exception("Test error")

        # Call function and check for exception
        with pytest.raises(Exception):
            load_json_chunks("test.json")


class TestCompareChunksByType:
    """Tests for the compare_chunks_by_type function."""

    def test_compare_identical_chunks(self):
        """Test comparing identical chunks by type."""
        # Create test chunks
        original_chunks = [
            {"type": "title", "text": "Title"},
            {"type": "scene_heading", "text": "INT. LIVING ROOM - DAY"},
            {"type": "action", "text": "John enters the room."},
        ]

        parsed_chunks = [
            {"type": "title", "text": "Title"},
            {"type": "scene_heading", "text": "INT. LIVING ROOM - DAY"},
            {"type": "action", "text": "John enters the room."},
        ]

        # Call function
        comparison = compare_chunks_by_type(original_chunks, parsed_chunks)

        # Check result
        assert comparison["title"]["original"] == 1
        assert comparison["title"]["parsed"] == 1
        assert comparison["title"]["diff"] == 0

        assert comparison["scene_heading"]["original"] == 1
        assert comparison["scene_heading"]["parsed"] == 1
        assert comparison["scene_heading"]["diff"] == 0

        assert comparison["action"]["original"] == 1
        assert comparison["action"]["parsed"] == 1
        assert comparison["action"]["diff"] == 0

    def test_compare_different_chunks(self):
        """Test comparing different chunks by type."""
        # Create test chunks
        original_chunks = [
            {"type": "title", "text": "Title"},
            {"type": "scene_heading", "text": "INT. LIVING ROOM - DAY"},
            {"type": "action", "text": "John enters the room."},
        ]

        parsed_chunks = [
            {"type": "title", "text": "Title"},
            {"type": "scene_heading", "text": "INT. LIVING ROOM - DAY"},
            {"type": "scene_heading", "text": "EXT. GARDEN - DAY"},
            {"type": "dialogue", "speaker": "JOHN", "text": "Hello"},
        ]

        # Call function
        comparison = compare_chunks_by_type(original_chunks, parsed_chunks)

        # Check result
        assert comparison["title"]["original"] == 1
        assert comparison["title"]["parsed"] == 1
        assert comparison["title"]["diff"] == 0

        assert comparison["scene_heading"]["original"] == 1
        assert comparison["scene_heading"]["parsed"] == 2
        assert comparison["scene_heading"]["diff"] == 1

        assert comparison["action"]["original"] == 1
        assert comparison["action"]["parsed"] == 0
        assert comparison["action"]["diff"] == -1

        assert comparison["dialogue"]["original"] == 0
        assert comparison["dialogue"]["parsed"] == 1
        assert comparison["dialogue"]["diff"] == 1


class TestAnalyzeChunksMisalignment:
    """Validate that analyze_chunks realigns after an extra parser chunk."""

    def test_realignment_after_extra_parser_chunk(self, caplog):
        """
        The parser output contains an extra chunk *before* the lists diverge.
        The function should report exactly one 'additional' chunk and no
        'missing' chunks – proving that the bidirectional look-ahead
        prevents the cascade of false positives.
        """
        from script_to_speech.parser import regression_check as rc

        with (
            patch(
                "script_to_speech.parser.regression_check.compare_chunks",
                return_value=[],
            ),
            patch(
                "script_to_speech.parser.regression_check.get_chunk_snippet",
                side_effect=lambda c: c["raw_text"][:20],
            ),
        ):
            input_chunks = [
                {"type": "action", "raw_text": "Line A", "text": "Line A"},
                {"type": "action", "raw_text": "Line B", "text": "Line B"},
                {"type": "action", "raw_text": "Line C", "text": "Line C"},
            ]

            parser_chunks = [
                {"type": "action", "raw_text": "Line A", "text": "Line A"},
                {
                    "type": "action",
                    "raw_text": "Line EXTRA",
                    "text": "Line EXTRA",
                },  # extra
                {"type": "action", "raw_text": "Line B", "text": "Line B"},
                {"type": "action", "raw_text": "Line C", "text": "Line C"},
            ]

            caplog.set_level(
                logging.INFO, logger="script_to_speech.parser.regression_check"
            )
            analyze_chunks(input_chunks, parser_chunks)

        log_text = caplog.text
        assert "Current parser generates 1 chunks not in the input" in log_text
        # No 'Input has … chunks that the current parser doesn't generate' message
        assert "Input has" not in log_text


# --------------------------------------------------------------------------- #
#  run_regression_check() orchestration tests
# --------------------------------------------------------------------------- #
class TestRunRegressionCheck:
    """Tests for the run_regression_check function."""

    @patch("script_to_speech.parser.regression_check.setup_logging")
    @patch("script_to_speech.parser.regression_check.load_json_chunks")
    @patch("script_to_speech.parser.regression_check.ScreenplayParser")
    @patch("script_to_speech.parser.regression_check.process_chunks")
    @patch("script_to_speech.parser.regression_check.compare_chunks_by_type")
    @patch("script_to_speech.parser.regression_check.log_chunk_comparison")
    @patch("script_to_speech.parser.regression_check.analyze_chunks")
    @patch("builtins.open", new_callable=mock_open)
    def test_run_regression_check(
        self,
        mock_file_open,
        mock_analyze,
        mock_log_comparison,
        mock_compare,
        mock_process,
        mock_parser,
        mock_load,
        mock_setup_logging,
    ):
        """Test running regression check."""
        # Mock setup_logging
        mock_setup_logging.return_value = "test.log"

        # Mock load_json_chunks
        input_chunks = [
            {"type": "title", "text": "Title"},
            {"type": "scene_heading", "text": "INT. LIVING ROOM - DAY"},
        ]
        mock_load.return_value = input_chunks

        # Mock ScreenplayParser
        mock_parser_instance = MagicMock()
        mock_parser.return_value = mock_parser_instance

        # Mock process_chunks
        parser_chunks = [
            {"type": "title", "text": "Title"},
            {"type": "scene_heading", "text": "INT. LIVING ROOM - DAY"},
        ]
        mock_process.return_value = parser_chunks

        # Mock compare_chunks_by_type
        comparison = {
            "title": {"original": 1, "parsed": 1, "diff": 0},
            "scene_heading": {"original": 1, "parsed": 1, "diff": 0},
        }
        mock_compare.return_value = comparison

        # Call function
        run_regression_check("test.json")

        # Check that setup_logging was called
        mock_setup_logging.assert_called_once_with("test.json")

        # Check that load_json_chunks was called
        mock_load.assert_called_once_with("test.json")

        # Check that ScreenplayParser was initialized
        mock_parser.assert_called_once()

        # Check that process_chunks was called
        mock_process.assert_called_once_with(input_chunks, mock_parser_instance)

        # Check that compare_chunks_by_type was called
        mock_compare.assert_called_once_with(input_chunks, parser_chunks)

        # Check that log_chunk_comparison was called
        mock_log_comparison.assert_called_once_with(comparison)

        # Check that analyze_chunks was called
        mock_analyze.assert_called_once_with(input_chunks, parser_chunks)

        # Check that output file was written
        mock_file_open.assert_called()

    @patch("script_to_speech.parser.regression_check.setup_logging")
    @patch("script_to_speech.parser.regression_check.load_json_chunks")
    def test_run_regression_check_error(self, mock_load, mock_setup_logging):
        """Test error handling in run_regression_check."""
        # Mock setup_logging
        mock_setup_logging.return_value = "test.log"

        # Mock load_json_chunks to raise an exception
        mock_load.side_effect = Exception("Test error")

        # Call function and check for exception
        with pytest.raises(SystemExit):
            run_regression_check("test.json")


class TestMain:
    """Tests for the main function."""

    @patch("script_to_speech.parser.regression_check.run_regression_check")
    @patch("argparse.ArgumentParser.parse_args")
    def test_main_function(self, mock_parse_args, mock_run):
        """Test the main function."""
        # Mock command line arguments
        mock_args = MagicMock()
        mock_args.input_file = "test.json"
        mock_args.debug = False
        mock_parse_args.return_value = mock_args

        # Call function
        main()

        # Check that run_regression_check was called with correct arguments
        mock_run.assert_called_once_with("test.json", False)

    @patch("script_to_speech.parser.regression_check.run_regression_check")
    @patch("argparse.ArgumentParser.parse_args")
    def test_main_function_with_debug(self, mock_parse_args, mock_run):
        """Test the main function with debug flag."""
        # Mock command line arguments
        mock_args = MagicMock()
        mock_args.input_file = "test.json"
        mock_args.debug = True
        mock_parse_args.return_value = mock_args

        # Call function
        main()

        # Check that run_regression_check was called with correct arguments
        mock_run.assert_called_once_with("test.json", True)
