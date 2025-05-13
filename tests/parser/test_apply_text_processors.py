"""
Unit tests for the apply_text_processors module in the parser package.

This module focuses on testing the functionality for applying text processors
to screenplay JSON chunks.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

from src.script_to_speech.parser.apply_text_processors import (  # Corrected import path
    apply_text_processors,
    main,
)


class TestApplyTextProcessors:
    """Tests for the apply_text_processors function."""

    @patch("src.script_to_speech.parser.apply_text_processors.TextProcessorManager")
    @patch("src.script_to_speech.parser.apply_text_processors.setup_parser_logging")
    @patch(
        "src.script_to_speech.parser.apply_text_processors.get_text_processor_configs"
    )
    @patch("src.script_to_speech.parser.apply_text_processors.sanitize_name")
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

        # Set up different mock responses based on file path
        def mock_open_side_effect(file_path, *args, **kwargs):
            mock = MagicMock()
            mock.__enter__ = MagicMock()
            mock.__exit__ = MagicMock()

            # For JSON file
            if str(file_path).endswith(".json"):
                mock.__enter__.return_value.read.return_value = json.dumps(chunks)
            # For YAML config file
            elif str(file_path).endswith(".yaml"):
                mock.__enter__.return_value.read.return_value = """
preprocessors:
  - name: skip_and_merge
    config:
      skip_types:
        - page_number
processors:
  - name: skip_empty
    config:
      skip_types:
        - page_number
"""
            return mock

        mock_file_open.side_effect = mock_open_side_effect

        # Mock sanitize_name
        mock_sanitize.return_value = "test_screenplay"

        # Mock get_text_processor_configs
        mock_config_path = Path("config.yaml")
        mock_get_configs.return_value = [mock_config_path]

        # Set up mock processor manager
        mock_manager_instance = MagicMock()
        mock_manager_instance.process_chunks.return_value = [
            {"type": "title", "text": "TITLE"},
            {"type": "scene_heading", "text": "INT. LIVING ROOM - DAY"},
            {"type": "action", "text": "JOHN ENTERS THE ROOM."},
        ]
        mock_manager.return_value = mock_manager_instance

        # Call function with Path object
        input_path = Path("test_screenplay.json")
        apply_text_processors(input_path)

        # Check that logging was set up
        mock_setup_logging.assert_called_once()

        # Check that processor manager was initialized with Path
        mock_manager.assert_called_once_with([mock_config_path])

        # Check that process_chunks was called
        mock_manager_instance.process_chunks.assert_called_once_with(chunks)

        # Check that output file was written (open accepts Path)
        mock_file_open.assert_any_call(input_path, "r", encoding="utf-8")
        assert any("w" in call.args for call in mock_file_open.call_args_list)

    @patch("src.script_to_speech.parser.apply_text_processors.TextProcessorManager")
    @patch("src.script_to_speech.parser.apply_text_processors.setup_parser_logging")
    @patch(
        "src.script_to_speech.parser.apply_text_processors.get_text_processor_configs"
    )
    @patch("src.script_to_speech.parser.apply_text_processors.sanitize_name")
    @patch("builtins.open", new_callable=mock_open)
    def test_apply_text_processors_with_dialogue(
        self,
        mock_file_open,
        mock_sanitize,
        mock_get_configs,
        mock_setup_logging,
        mock_manager,
    ):
        """Test applying text processors to chunks with dialogue."""
        # Create test chunks
        chunks = [
            {"type": "scene_heading", "text": "INT. LIVING ROOM - DAY"},
            {"type": "action", "text": "John enters the room."},
            {"type": "speaker_attribution", "speaker": "", "text": "JOHN"},
            {"type": "dialogue", "speaker": "JOHN", "text": "Hello, how are you?"},
        ]

        # Set up different mock responses based on file path
        def mock_open_side_effect(file_path, *args, **kwargs):
            mock = MagicMock()
            mock.__enter__ = MagicMock()
            mock.__exit__ = MagicMock()

            # For JSON file
            if str(file_path).endswith(".json"):
                mock.__enter__.return_value.read.return_value = json.dumps(chunks)
            # For YAML config file
            elif str(file_path).endswith(".yaml"):
                mock.__enter__.return_value.read.return_value = """
preprocessors:
  - name: skip_and_merge
    config:
      skip_types:
        - page_number
processors:
  - name: skip_empty
    config:
      skip_types:
        - page_number
"""
            return mock

        mock_file_open.side_effect = mock_open_side_effect

        # Mock sanitize_name
        mock_sanitize.return_value = "test_screenplay"

        # Mock get_text_processor_configs
        mock_config_path = Path("config.yaml")
        mock_get_configs.return_value = [mock_config_path]

        # Set up mock processor manager
        mock_manager_instance = MagicMock()
        processed_chunks = [
            {"type": "scene_heading", "text": "INT. LIVING ROOM - DAY"},
            {"type": "action", "text": "John enters the room."},
            {"type": "speaker_attribution", "speaker": "", "text": "JOHN"},
            {
                "type": "dialogue",
                "speaker": "JOHN",
                "text": "Hello, how are you? (emphatically)",
            },
        ]
        mock_manager_instance.process_chunks.return_value = processed_chunks
        mock_manager.return_value = mock_manager_instance

        # Call function with Path objects
        input_path = Path("test_screenplay.json")
        custom_config_paths = [Path("custom_config.yaml")]
        output_path_obj = Path("output.json")
        apply_text_processors(input_path, custom_config_paths, output_path_obj)

        # Check that logging was set up
        mock_setup_logging.assert_called_once()

        # Check that get_text_processor_configs was called with correct Path arguments
        mock_get_configs.assert_called_once_with(input_path, custom_config_paths)

        # Check that processor manager was initialized with Path
        mock_manager.assert_called_once_with([mock_config_path])

        # Check that process_chunks was called
        mock_manager_instance.process_chunks.assert_called_once_with(chunks)

        # Check that input file was read (open accepts Path)
        mock_file_open.assert_any_call(input_path, "r", encoding="utf-8")

        # Check that write operations were performed by checking call_args_list
        write_operations = [
            call
            for call in mock_file_open.call_args_list
            if len(call[0]) >= 2 and call[0][1] == "w"
        ]
        assert write_operations, "No write operations were performed"

        # Check that the output file was opened for writing (open accepts Path)
        output_file_written = False
        for call in mock_file_open.call_args_list:
            args, kwargs = call
            # Check if the first argument is the expected Path object and mode is 'w'
            if len(args) >= 2 and args[0] == output_path_obj and args[1] == "w":
                output_file_written = True
                break

        assert output_file_written, "Output file was not written to"

    @patch("src.script_to_speech.parser.apply_text_processors.apply_text_processors")
    @patch("argparse.ArgumentParser.parse_args")
    def test_main_function(self, mock_parse_args, mock_apply):
        """Test the main function."""
        # Mock command line arguments
        mock_args = MagicMock()
        mock_args.json_file = "test_screenplay.json"
        mock_args.text_processor_configs = ["config.yaml"]
        mock_args.output_path = "output.json"
        mock_parse_args.return_value = mock_args

        # Call function
        main()

        # Check that apply_text_processors was called with correct Path arguments
        # Note: The main function converts args to Path before calling
        mock_apply.assert_called_once_with(
            Path("test_screenplay.json"), [Path("config.yaml")], Path("output.json")
        )

    @patch("src.script_to_speech.parser.apply_text_processors.apply_text_processors")
    @patch("argparse.ArgumentParser.parse_args")
    def test_main_function_with_error(self, mock_parse_args, mock_apply):
        """Test the main function with an error."""
        # Mock command line arguments
        mock_args = MagicMock()
        mock_args.json_file = "test_screenplay.json"
        mock_args.text_processor_configs = ["config.yaml"]
        mock_args.output_path = "output.json"
        mock_parse_args.return_value = mock_args

        # Mock apply_text_processors to raise an exception
        mock_apply.side_effect = Exception("Test error")

        # Call function
        with pytest.raises(SystemExit):
            main()
