"""
Unit tests for the apply_text_processors module in the parser package.

This module focuses on testing the functionality for applying text processors
to screenplay JSON chunks.
"""

import json
from parser.apply_text_processors import apply_text_processors, main
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest


class TestApplyTextProcessors:
    """Tests for the apply_text_processors function."""

    @patch("parser.apply_text_processors.TextProcessorManager")
    @patch("parser.apply_text_processors.setup_parser_logging")
    @patch("parser.apply_text_processors.get_processor_configs")
    @patch("parser.apply_text_processors.sanitize_name")
    @patch("builtins.open", new_callable=mock_open)
    def test_apply_text_processors_basic(
        self,
        mock_file_open,
        mock_sanitize,
        mock_get_configs,
        mock_setup_logging,
        mock_manager,
    ):
        """Test applying text processors to basic chunks."""
        # Create test chunks
        chunks = [
            {"type": "title", "text": "Title"},
            {"type": "scene_heading", "text": "INT. LIVING ROOM - DAY"},
            {"type": "action", "text": "John enters the room."},
        ]

        # Set up mock file content
        mock_file_open.return_value.__enter__.return_value.read.return_value = (
            json.dumps(chunks)
        )

        # Mock sanitize_name
        mock_sanitize.return_value = "test_screenplay"

        # Mock get_processor_configs
        mock_get_configs.return_value = ["config.yaml"]

        # Set up mock processor manager
        mock_manager_instance = MagicMock()
        mock_manager_instance.process_chunks.return_value = [
            {"type": "title", "text": "TITLE"},
            {"type": "scene_heading", "text": "INT. LIVING ROOM - DAY"},
            {"type": "action", "text": "JOHN ENTERS THE ROOM."},
        ]
        mock_manager.return_value = mock_manager_instance

        # Call function
        apply_text_processors("test_screenplay.json")

        # Check that logging was set up
        mock_setup_logging.assert_called_once()

        # Check that processor manager was initialized
        mock_manager.assert_called_once_with(["config.yaml"])

        # Check that process_chunks was called
        mock_manager_instance.process_chunks.assert_called_once_with(chunks)

        # Check that output file was written
        mock_file_open.assert_any_call("test_screenplay.json", "r", encoding="utf-8")
        assert any("w" in call.args for call in mock_file_open.call_args_list)

    @patch("parser.apply_text_processors.TextProcessorManager")
    @patch("parser.apply_text_processors.setup_parser_logging")
    @patch("parser.apply_text_processors.get_processor_configs")
    @patch("parser.apply_text_processors.sanitize_name")
    @patch("builtins.open", new_callable=mock_open)
    def test_apply_text_processors_with_dialog(
        self,
        mock_file_open,
        mock_sanitize,
        mock_get_configs,
        mock_setup_logging,
        mock_manager,
    ):
        """Test applying text processors to chunks with dialog."""
        # Create test chunks
        chunks = [
            {"type": "scene_heading", "text": "INT. LIVING ROOM - DAY"},
            {"type": "action", "text": "John enters the room."},
            {"type": "speaker_attribution", "speaker": "", "text": "JOHN"},
            {"type": "dialog", "speaker": "JOHN", "text": "Hello, how are you?"},
        ]

        # Set up mock file content
        mock_file_open.return_value.__enter__.return_value.read.return_value = (
            json.dumps(chunks)
        )

        # Mock sanitize_name
        mock_sanitize.return_value = "test_screenplay"

        # Mock get_processor_configs
        mock_get_configs.return_value = ["config.yaml"]

        # Set up mock processor manager
        mock_manager_instance = MagicMock()
        processed_chunks = [
            {"type": "scene_heading", "text": "INT. LIVING ROOM - DAY"},
            {"type": "action", "text": "John enters the room."},
            {"type": "speaker_attribution", "speaker": "", "text": "JOHN"},
            {
                "type": "dialog",
                "speaker": "JOHN",
                "text": "Hello, how are you? (emphatically)",
            },
        ]
        mock_manager_instance.process_chunks.return_value = processed_chunks
        mock_manager.return_value = mock_manager_instance

        # Call function
        apply_text_processors(
            "test_screenplay.json", ["custom_config.yaml"], "output.json"
        )

        # Check that logging was set up
        mock_setup_logging.assert_called_once()

        # Check that get_processor_configs was called with correct arguments
        mock_get_configs.assert_called_once_with(
            "test_screenplay.json", ["custom_config.yaml"]
        )

        # Check that processor manager was initialized
        mock_manager.assert_called_once_with(["config.yaml"])

        # Check that process_chunks was called
        mock_manager_instance.process_chunks.assert_called_once_with(chunks)

        # Check that input file was read
        mock_file_open.assert_any_call("test_screenplay.json", "r", encoding="utf-8")

        # Check that some write operation was performed
        assert mock_file_open().write.called

        # For the output file, we can't use assert_any_call directly because the Path object
        # might be used instead of a string. Let's check the call args list more flexibly.
        output_file_written = False
        for call in mock_file_open.call_args_list:
            args, kwargs = call
            if len(args) >= 2 and str(args[0]) == "output.json" and args[1] == "w":
                output_file_written = True
                break

        assert output_file_written, "Output file was not written to"

    @patch("parser.apply_text_processors.apply_text_processors")
    @patch("argparse.ArgumentParser.parse_args")
    def test_main_function(self, mock_parse_args, mock_apply):
        """Test the main function."""
        # Mock command line arguments
        mock_args = MagicMock()
        mock_args.json_file = "test_screenplay.json"
        mock_args.processor_configs = ["config.yaml"]
        mock_args.output_path = "output.json"
        mock_parse_args.return_value = mock_args

        # Call function
        main()

        # Check that apply_text_processors was called with correct arguments
        mock_apply.assert_called_once_with(
            "test_screenplay.json", ["config.yaml"], "output.json"
        )

    @patch("parser.apply_text_processors.apply_text_processors")
    @patch("argparse.ArgumentParser.parse_args")
    def test_main_function_with_error(self, mock_parse_args, mock_apply):
        """Test the main function with an error."""
        # Mock command line arguments
        mock_args = MagicMock()
        mock_args.json_file = "test_screenplay.json"
        mock_args.processor_configs = ["config.yaml"]
        mock_args.output_path = "output.json"
        mock_parse_args.return_value = mock_args

        # Mock apply_text_processors to raise an exception
        mock_apply.side_effect = Exception("Test error")

        # Call function
        with pytest.raises(SystemExit):
            main()
