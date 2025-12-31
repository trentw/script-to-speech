"""
Unit tests for the process module in the parser package.

This module focuses on testing the functionality for processing screenplay files
(PDF or TXT) to generate JSON chunks.
"""

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

from script_to_speech.parser.process import (
    main,
    process_screenplay,
    remove_strings_preserve_layout,
)


@pytest.mark.unit
class TestProcessScreenplay:
    """Tests for the process_screenplay function."""

    @patch("script_to_speech.parser.process.extract_text_preserving_whitespace")
    @patch("script_to_speech.parser.process.ScreenplayParser")
    @patch("script_to_speech.parser.process.create_output_folders")
    @patch("script_to_speech.parser.process.setup_parser_logging")
    @patch("script_to_speech.parser.process.generate_optional_config")
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
        mock_parser,
        mock_extract_text,
    ):
        """Test processing a PDF file."""
        # Mock file existence
        mock_exists.return_value = True

        # Mock file comparison
        mock_samefile.return_value = False

        # Mock folder creation
        mock_create_folders.return_value = (
            Path("/path/to/screenplay"),
            Path("/path/to/cache"),
            Path("/path/to/logs"),
            Path("/path/to/log"),
        )

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

        # Check that text was extracted
        mock_extract_text.assert_called_once()

        # Check that parser was called
        mock_parser.assert_called_once()
        mock_parser_instance.parse_screenplay.assert_called_once_with("Extracted text")

        # Check that JSON was written
        mock_file_open.assert_called()

        # Check that config was generated
        mock_generate_config.assert_called_once()

    @patch("script_to_speech.parser.process.extract_text_preserving_whitespace")
    @patch("script_to_speech.parser.process.ScreenplayParser")
    @patch("script_to_speech.parser.process.create_output_folders")
    @patch("script_to_speech.parser.process.setup_parser_logging")
    @patch("script_to_speech.parser.process.generate_optional_config")
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
        mock_parser,
        mock_extract_text,
    ):
        """Test processing a TXT file."""
        # Mock file existence
        mock_exists.return_value = True

        # Mock file comparison
        mock_samefile.return_value = False

        # Mock folder creation
        mock_create_folders.return_value = (
            Path("/path/to/screenplay"),
            Path("/path/to/cache"),
            Path("/path/to/logs"),
            Path("/path/to/log"),
        )

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

    @patch("script_to_speech.parser.process.process_screenplay")
    @patch("argparse.ArgumentParser.parse_args")
    def test_main_function(self, mock_parse_args, mock_process):
        """Test the main function."""
        # Mock command line arguments
        mock_args = MagicMock()
        mock_args.input_file = "test.pdf"
        mock_args.output_dir = None
        mock_args.text_only = False
        mock_args.remove = None
        mock_args.remove_lines = 2
        mock_parse_args.return_value = mock_args

        # Mock process_screenplay return value
        mock_process.return_value = {"output_dir": "/test", "removal_metadata": None}

        # Call function
        main()

        # Check that process_screenplay was called with correct arguments
        mock_process.assert_called_once_with(
            "test.pdf", None, False, strings_to_remove=None, remove_lines=2
        )

    @patch("script_to_speech.parser.process.process_screenplay")
    @patch("argparse.ArgumentParser.parse_args")
    def test_main_function_with_error(self, mock_parse_args, mock_process):
        """Test the main function with an error."""
        # Mock command line arguments
        mock_args = MagicMock()
        mock_args.input_file = "test.pdf"
        mock_args.output_dir = None
        mock_args.text_only = False
        mock_args.remove = None
        mock_args.remove_lines = 2
        mock_parse_args.return_value = mock_args

        # Mock process_screenplay to raise an exception
        mock_process.side_effect = Exception("Test error")

        # Call function
        with pytest.raises(SystemExit):
            main()

    @patch("script_to_speech.parser.process.process_screenplay")
    @patch("argparse.ArgumentParser.parse_args")
    def test_main_function_with_remove_option(self, mock_parse_args, mock_process):
        """Test the main function with --remove option."""
        # Mock command line arguments
        mock_args = MagicMock()
        mock_args.input_file = "test.pdf"
        mock_args.output_dir = None
        mock_args.text_only = False
        mock_args.remove = ["HEADER TEXT", "FOOTER TEXT"]
        mock_args.remove_lines = 2
        mock_parse_args.return_value = mock_args

        # Mock process_screenplay return value
        mock_process.return_value = {
            "output_dir": "/test",
            "removal_metadata": {
                "patterns_removed": ["HEADER TEXT", "FOOTER TEXT"],
                "total_removals": 50,
                "per_pattern_counts": {"HEADER TEXT": 30, "FOOTER TEXT": 20},
            },
        }

        # Call function
        main()

        # Check that process_screenplay was called with strings_to_remove and remove_lines
        mock_process.assert_called_once_with(
            "test.pdf",
            None,
            False,
            strings_to_remove=["HEADER TEXT", "FOOTER TEXT"],
            remove_lines=2,
        )


@pytest.mark.unit
class TestRemoveStringsPreserveLayout:
    """Tests for the remove_strings_preserve_layout function."""

    def test_remove_single_pattern(self):
        """Test removing a single pattern."""
        # Arrange
        text = "HEADER TEXT\nContent here\nHEADER TEXT"
        patterns = ["HEADER TEXT"]

        # Act
        result, metadata = remove_strings_preserve_layout(text, patterns)

        # Assert
        assert result == "           \nContent here\n           "
        assert metadata["total_removals"] == 2
        assert metadata["per_pattern_counts"]["HEADER TEXT"] == 2

    def test_remove_multiple_patterns(self):
        """Test removing multiple patterns."""
        # Arrange
        text = "HEADER\nContent\nFOOTER"
        patterns = ["HEADER", "FOOTER"]

        # Act
        result, metadata = remove_strings_preserve_layout(text, patterns)

        # Assert
        assert result == "      \nContent\n      "
        assert metadata["total_removals"] == 2
        assert len(metadata["patterns_removed"]) == 2

    def test_preserve_spacing(self):
        """Test that replacement preserves layout with equal-length spaces."""
        # Arrange
        text = "   HEADER   3.\nDialogue here"
        patterns = ["HEADER"]

        # Act
        result, metadata = remove_strings_preserve_layout(text, patterns)

        # Assert
        # "HEADER" (6 chars) replaced with 6 spaces: "   " + 6 spaces + "   3."
        assert result == "            3.\nDialogue here"
        assert len(result) == len(text)

    def test_pattern_not_found(self):
        """Test when pattern is not found in text."""
        # Arrange
        text = "Content without pattern"
        patterns = ["NONEXISTENT"]

        # Act
        result, metadata = remove_strings_preserve_layout(text, patterns)

        # Assert
        assert result == text  # Unchanged
        assert metadata["total_removals"] == 0
        assert metadata["patterns_removed"] == []

    def test_empty_patterns_list(self):
        """Test with empty patterns list."""
        # Arrange
        text = "Some content"
        patterns = []

        # Act
        result, metadata = remove_strings_preserve_layout(text, patterns)

        # Assert
        assert result == text
        assert metadata["total_removals"] == 0

    def test_empty_pattern_in_list(self):
        """Test that empty patterns are skipped."""
        # Arrange
        text = "HEADER\nContent"
        patterns = ["", "HEADER", ""]

        # Act
        result, metadata = remove_strings_preserve_layout(text, patterns)

        # Assert
        assert result == "      \nContent"
        assert metadata["total_removals"] == 1

    def test_overlapping_patterns(self):
        """Test with patterns that could overlap."""
        # Arrange
        text = "HEADER TEXT HEADER"
        patterns = ["HEADER TEXT", "HEADER"]

        # Act
        result, metadata = remove_strings_preserve_layout(text, patterns)

        # Assert
        # First pattern replaces "HEADER TEXT", second replaces remaining "HEADER"
        # "HEADER TEXT HEADER" -> "            HEADER" -> "                  "
        assert "HEADER" not in result
        assert metadata["total_removals"] == 2

    def test_unicode_text(self):
        """Test with unicode content (after unidecode normalization)."""
        # Arrange
        text = "SCRIPT TITLE - Version 1.0\nDialogue"
        patterns = ["SCRIPT TITLE - Version 1.0"]

        # Act
        result, metadata = remove_strings_preserve_layout(text, patterns)

        # Assert
        assert result == "                          \nDialogue"
        assert metadata["total_removals"] == 1


@pytest.mark.unit
class TestRemoveFromHeaderFooterPositions:
    """Tests for position-restricted header/footer removal."""

    def test_removes_from_header_not_dialogue(self):
        """Test that patterns in headers are removed but same text in dialogue is preserved."""
        from unittest.mock import MagicMock, patch

        from script_to_speech.parser.process import remove_from_header_footer_positions
        from script_to_speech.parser.utils.text_utils import PageText

        # Create mock pages where "MY LOVE" appears in header (line 1) and middle dialogue
        # Need enough lines so dialogue is NOT in header/footer region (lines_to_scan=2)
        mock_pages = [
            PageText(
                page_number=1,
                text="MY LOVE - A Script\nSecond header line\n\nINT. BEDROOM - DAY\n\nALICE\nMY LOVE, where are you?\n\nBOB\nI'm right here.\n\nFooter line 1\nFooter line 2",
            ),
        ]

        with patch(
            "script_to_speech.parser.process.extract_text_by_page",
            return_value=mock_pages,
        ):
            # Act - remove "MY LOVE" from first 2 lines only
            result, metadata = remove_from_header_footer_positions(
                "fake.pdf", ["MY LOVE"], lines_to_scan=2
            )

            # Assert - header should be removed, dialogue preserved
            # First line: "MY LOVE - A Script" -> "        - A Script"
            # Dialogue line should still have "MY LOVE"
            assert "MY LOVE, where are you?" in result  # Dialogue preserved
            assert result.startswith("        - A Script")  # Header removed
            assert metadata["total_removals"] == 1
            assert metadata["per_pattern_counts"]["MY LOVE"] == 1

    def test_removes_from_footer_not_dialogue(self):
        """Test that patterns in footers are removed but same text in dialogue is preserved."""
        from unittest.mock import patch

        from script_to_speech.parser.process import remove_from_header_footer_positions
        from script_to_speech.parser.utils.text_utils import PageText

        # Footer with "THE END" - dialogue mentioning it is in the middle, away from footer
        mock_pages = [
            PageText(
                page_number=1,
                text="Header line 1\nHeader line 2\n\nBOB\nThis is THE END of the road.\n\nALICE\nI agree.\n\nFooter line\nTHE END",
            ),
        ]

        with patch(
            "script_to_speech.parser.process.extract_text_by_page",
            return_value=mock_pages,
        ):
            result, metadata = remove_from_header_footer_positions(
                "fake.pdf", ["THE END"], lines_to_scan=2
            )

            # Assert - footer removed, dialogue preserved
            assert "This is THE END of the road." in result  # Dialogue preserved
            assert result.endswith("       ")  # Footer "THE END" replaced with spaces
            assert metadata["total_removals"] == 1

    def test_removes_from_both_header_and_footer(self):
        """Test removal from both header and footer positions."""
        from unittest.mock import patch

        from script_to_speech.parser.process import remove_from_header_footer_positions
        from script_to_speech.parser.utils.text_utils import PageText

        mock_pages = [
            PageText(
                page_number=1,
                text="HEADER TEXT\n\nMiddle content\n\nFOOTER TEXT",
            ),
        ]

        with patch(
            "script_to_speech.parser.process.extract_text_by_page",
            return_value=mock_pages,
        ):
            result, metadata = remove_from_header_footer_positions(
                "fake.pdf", ["HEADER TEXT", "FOOTER TEXT"], lines_to_scan=2
            )

            assert "           " in result  # HEADER TEXT replaced
            assert result.endswith("           ")  # FOOTER TEXT replaced
            assert "Middle content" in result
            assert metadata["total_removals"] == 2

    def test_respects_lines_to_scan_parameter(self):
        """Test that lines_to_scan controls how many lines are checked."""
        from unittest.mock import patch

        from script_to_speech.parser.process import remove_from_header_footer_positions
        from script_to_speech.parser.utils.text_utils import PageText

        # Pattern on line 3 (should be removed with lines_to_scan=3, not with 2)
        mock_pages = [
            PageText(
                page_number=1,
                text="Line 1\nLine 2\nPATTERN LINE 3\n\nMiddle\n\nLine -3\nLine -2\nLine -1",
            ),
        ]

        with patch(
            "script_to_speech.parser.process.extract_text_by_page",
            return_value=mock_pages,
        ):
            # With lines_to_scan=2, pattern should NOT be removed
            result2, meta2 = remove_from_header_footer_positions(
                "fake.pdf", ["PATTERN LINE 3"], lines_to_scan=2
            )
            assert "PATTERN LINE 3" in result2
            assert meta2["total_removals"] == 0

            # With lines_to_scan=3, pattern SHOULD be removed
            result3, meta3 = remove_from_header_footer_positions(
                "fake.pdf", ["PATTERN LINE 3"], lines_to_scan=3
            )
            assert "PATTERN LINE 3" not in result3
            assert meta3["total_removals"] == 1

    def test_skips_blank_lines_when_counting(self):
        """Test that blank lines don't count toward N lines to scan."""
        from unittest.mock import patch

        from script_to_speech.parser.process import remove_from_header_footer_positions
        from script_to_speech.parser.utils.text_utils import PageText

        # Blank lines between header content
        mock_pages = [
            PageText(
                page_number=1,
                text="\n\nHEADER LINE 1\n\n\nHEADER LINE 2\n\nMiddle content",
            ),
        ]

        with patch(
            "script_to_speech.parser.process.extract_text_by_page",
            return_value=mock_pages,
        ):
            result, metadata = remove_from_header_footer_positions(
                "fake.pdf", ["HEADER LINE 1", "HEADER LINE 2"], lines_to_scan=2
            )

            # Both should be removed (blank lines don't count)
            assert "HEADER LINE 1" not in result
            assert "HEADER LINE 2" not in result
            assert metadata["total_removals"] == 2

    def test_multiple_pages(self):
        """Test removal works across multiple pages."""
        from unittest.mock import patch

        from script_to_speech.parser.process import remove_from_header_footer_positions
        from script_to_speech.parser.utils.text_utils import PageText

        mock_pages = [
            PageText(page_number=1, text="HEADER\n\nPage 1 content\n\nFOOTER"),
            PageText(page_number=2, text="HEADER\n\nPage 2 content\n\nFOOTER"),
        ]

        with patch(
            "script_to_speech.parser.process.extract_text_by_page",
            return_value=mock_pages,
        ):
            result, metadata = remove_from_header_footer_positions(
                "fake.pdf", ["HEADER", "FOOTER"], lines_to_scan=2
            )

            # Check both pages are present (joined with no separator)
            assert "Page 1 content" in result
            assert "Page 2 content" in result
            # Check removals on both pages
            assert metadata["total_removals"] == 4
            assert metadata["per_pattern_counts"]["HEADER"] == 2
            assert metadata["per_pattern_counts"]["FOOTER"] == 2
