import re

import pytest

from script_to_speech.text_processors.preprocessors.extract_dialog_parentheticals_preprocessor import (
    ExtractDialogParentheticalsPreProcessor,
)


class TestExtractDialogParentheticalsPreProcessor:
    """Tests for the ExtractDialogParentheticalsPreProcessor class."""

    def test_validate_config_valid_empty(self):
        """Test validate_config with valid empty configuration."""
        # Arrange
        config = {}
        processor = ExtractDialogParentheticalsPreProcessor(config)

        # Act & Assert
        assert processor.validate_config() is True

    def test_validate_config_valid_max_words(self):
        """Test validate_config with valid max_words configuration."""
        # Arrange
        config = {"max_words": 5}
        processor = ExtractDialogParentheticalsPreProcessor(config)

        # Act & Assert
        assert processor.validate_config() is True

    def test_validate_config_valid_extract_only(self):
        """Test validate_config with valid extract_only configuration."""
        # Arrange
        config = {"extract_only": ["pause", "in french*"]}
        processor = ExtractDialogParentheticalsPreProcessor(config)

        # Act & Assert
        assert processor.validate_config() is True

    def test_validate_config_valid_extract_all_except(self):
        """Test validate_config with valid extract_all_except configuration."""
        # Arrange
        config = {"extract_all_except": ["quietly", "softly*"]}
        processor = ExtractDialogParentheticalsPreProcessor(config)

        # Act & Assert
        assert processor.validate_config() is True

    def test_validate_config_invalid_max_words(self):
        """Test validate_config with invalid max_words configuration."""
        # Arrange
        config = {"max_words": "not_an_int"}
        processor = ExtractDialogParentheticalsPreProcessor(config)

        # Act & Assert
        assert processor.validate_config() is False

    def test_validate_config_invalid_max_words_zero(self):
        """Test validate_config with max_words = 0 configuration."""
        # Arrange
        config = {"max_words": 0}
        processor = ExtractDialogParentheticalsPreProcessor(config)

        # Act & Assert
        assert processor.validate_config() is False

    def test_validate_config_invalid_mutually_exclusive(self):
        """Test validate_config with mutually exclusive configurations."""
        # Arrange
        config = {"extract_only": ["pause"], "extract_all_except": ["softly"]}
        processor = ExtractDialogParentheticalsPreProcessor(config)

        # Act & Assert
        assert processor.validate_config() is False

    def test_validate_config_invalid_extract_only_type(self):
        """Test validate_config with invalid extract_only type."""
        # Arrange
        config = {"extract_only": "not_a_list"}
        processor = ExtractDialogParentheticalsPreProcessor(config)

        # Act & Assert
        assert processor.validate_config() is False

    def test_count_words(self):
        """Test _count_words correctly counts words."""
        # Arrange
        processor = ExtractDialogParentheticalsPreProcessor({})
        text = "This has five words total"

        # Act
        word_count = processor._count_words(text)

        # Assert
        assert word_count == 5

    def test_should_extract_parenthetical_default(self):
        """Test _should_extract_parenthetical with default config."""
        # Arrange
        processor = ExtractDialogParentheticalsPreProcessor({})

        # Act & Assert - By default, all parentheticals should be extracted
        assert processor._should_extract_parenthetical("pause") is True
        assert processor._should_extract_parenthetical("speaking in French") is True
        assert (
            processor._should_extract_parenthetical(
                "a very long parenthetical that has many words"
            )
            is True
        )

    def test_should_extract_parenthetical_max_words(self):
        """Test _should_extract_parenthetical with max_words config."""
        # Arrange
        processor = ExtractDialogParentheticalsPreProcessor({"max_words": 3})

        # Act & Assert
        assert (
            processor._should_extract_parenthetical("short pause here") is True
        )  # 3 words
        assert (
            processor._should_extract_parenthetical("a very long pause") is False
        )  # 4 words
        assert processor._should_extract_parenthetical("pause") is True  # 1 word

    def test_should_extract_parenthetical_extract_only(self):
        """Test _should_extract_parenthetical with extract_only config."""
        # Arrange
        processor = ExtractDialogParentheticalsPreProcessor(
            {"extract_only": ["pause", "in french*"]}
        )

        # Act & Assert
        assert processor._should_extract_parenthetical("pause") is True  # Exact match
        assert (
            processor._should_extract_parenthetical("PAUSE") is True
        )  # Case insensitive
        assert (
            processor._should_extract_parenthetical("in french") is True
        )  # Starts with match due to *
        assert (
            processor._should_extract_parenthetical("in french accent") is True
        )  # Starts with match
        assert (
            processor._should_extract_parenthetical("speaking quickly") is False
        )  # No match

    def test_should_extract_parenthetical_extract_all_except(self):
        """Test _should_extract_parenthetical with extract_all_except config."""
        # Arrange
        processor = ExtractDialogParentheticalsPreProcessor(
            {"extract_all_except": ["quietly", "pause*"]}
        )

        # Act & Assert
        assert (
            processor._should_extract_parenthetical("quietly") is False
        )  # Exact match, should NOT extract
        assert (
            processor._should_extract_parenthetical("QUIETLY") is False
        )  # Case insensitive
        assert (
            processor._should_extract_parenthetical("pause") is False
        )  # Starts with match, should NOT extract
        assert (
            processor._should_extract_parenthetical("pause briefly") is False
        )  # Starts with match
        assert (
            processor._should_extract_parenthetical("speaking loudly") is True
        )  # No match, should extract

    def test_matches_pattern_exact(self):
        """Test _matches_pattern with exact match."""
        # Arrange
        processor = ExtractDialogParentheticalsPreProcessor({})

        # Act & Assert
        assert processor._matches_pattern("pause", "pause") is True
        assert processor._matches_pattern("pause", "PAUSE") is True  # Case insensitive
        assert (
            processor._matches_pattern("long pause", "pause") is True
        )  # Substring match
        assert processor._matches_pattern("breathing", "pause") is False  # No match

    def test_matches_pattern_partial(self):
        """Test _matches_pattern with partial match (asterisk)."""
        # Arrange
        processor = ExtractDialogParentheticalsPreProcessor({})

        # Act & Assert
        assert (
            processor._matches_pattern("pause", "pause*") is True
        )  # Exact match works
        assert (
            processor._matches_pattern("pauses", "pause*") is True
        )  # Begins with match
        assert (
            processor._matches_pattern("long pause", "pause*") is False
        )  # Doesn't begin with
        assert (
            processor._matches_pattern("PAUSE briefly", "pause*") is True
        )  # Case insensitive
        assert processor._matches_pattern("break", "pause*") is False  # No match

    def test_split_dialog_at_parenthetical(self):
        """Test _split_dialog_at_parenthetical splits dialog correctly."""
        # Arrange
        processor = ExtractDialogParentheticalsPreProcessor({})
        text = "This is text (with a parenthetical) in the middle."

        # Get the actual indices from re.search
        match = re.search(r"\(([^)]+)\)", text)
        start_idx = match.start()
        end_idx = match.end()
        parenthetical = match.group(0)

        chunk = {
            "type": "dialog",
            "speaker": "BOB",
            "text": text,
            "raw_text": "Original raw text",
        }

        # Act
        result = processor._split_dialog_at_parenthetical(
            chunk, start_idx, end_idx, parenthetical
        )

        # Assert
        assert len(result) == 3
        assert result[0]["type"] == "dialog"
        assert result[0]["speaker"] == "BOB"
        assert result[0]["text"] == "This is text"

        assert result[1]["type"] == "dialog_modifier"
        assert result[1]["speaker"] == ""
        assert result[1]["text"] == "(with a parenthetical)"

        assert result[2]["type"] == "dialog"
        assert result[2]["speaker"] == "BOB"
        assert result[2]["text"] == "in the middle."

    def test_split_dialog_at_parenthetical_start(self):
        """Test _split_dialog_at_parenthetical when parenthetical is at start."""
        # Arrange
        processor = ExtractDialogParentheticalsPreProcessor({})
        text = "(with a parenthetical) at the start."
        chunk = {
            "type": "dialog",
            "speaker": "BOB",
            "text": text,
            "raw_text": "Original raw text",
        }

        # Get the actual indices from re.search
        match = re.search(r"\(([^)]+)\)", text)
        start_idx = match.start()
        end_idx = match.end()
        parenthetical = match.group(0)

        # Act
        result = processor._split_dialog_at_parenthetical(
            chunk, start_idx, end_idx, parenthetical
        )

        # Assert
        assert len(result) == 2
        assert result[0]["type"] == "dialog_modifier"
        assert result[0]["speaker"] == ""
        assert result[0]["text"] == "(with a parenthetical)"

        assert result[1]["type"] == "dialog"
        assert result[1]["speaker"] == "BOB"
        assert result[1]["text"] == "at the start."

    def test_split_dialog_at_parenthetical_end(self):
        """Test _split_dialog_at_parenthetical when parenthetical is at end."""
        # Arrange
        processor = ExtractDialogParentheticalsPreProcessor({})
        text = "At the end (with a parenthetical)"

        # Get the actual indices from re.search
        match = re.search(r"\(([^)]+)\)", text)
        start_idx = match.start()
        end_idx = match.end()
        parenthetical = match.group(0)

        chunk = {
            "type": "dialog",
            "speaker": "BOB",
            "text": text,
            "raw_text": "Original raw text",
        }

        # Act
        result = processor._split_dialog_at_parenthetical(
            chunk, start_idx, end_idx, parenthetical
        )

        # Assert
        assert len(result) == 2
        assert result[0]["type"] == "dialog"
        assert result[0]["speaker"] == "BOB"
        assert result[0]["text"] == "At the end"

        assert result[1]["type"] == "dialog_modifier"
        assert result[1]["speaker"] == ""
        assert result[1]["text"] == "(with a parenthetical)"

    def test_process_empty_list(self):
        """Test process with empty chunks list."""
        # Arrange
        processor = ExtractDialogParentheticalsPreProcessor({})

        # Act
        result, changed = processor.process([])

        # Assert
        assert result == []
        assert changed is False

    def test_process_no_dialog_chunks(self):
        """Test process with no dialog chunks to extract parentheticals from."""
        # Arrange
        processor = ExtractDialogParentheticalsPreProcessor({})
        chunks = [
            {"type": "action", "text": "Action text"},
            {"type": "speaker_attribution", "text": "BOB"},
        ]

        # Act
        result, changed = processor.process(chunks)

        # Assert
        assert result == chunks
        assert changed is False

    def test_process_dialog_no_parentheticals(self):
        """Test process with dialog chunk but no parentheticals."""
        # Arrange
        processor = ExtractDialogParentheticalsPreProcessor({})
        chunks = [
            {
                "type": "dialog",
                "speaker": "BOB",
                "text": "Dialog with no parentheticals",
            },
        ]

        # Act
        result, changed = processor.process(chunks)

        # Assert
        assert result == chunks
        assert changed is False

    def test_process_extract_single_parenthetical(self):
        """Test process extracting a single parenthetical."""
        # Arrange
        processor = ExtractDialogParentheticalsPreProcessor({})
        chunks = [
            {
                "type": "dialog",
                "speaker": "BOB",
                "text": "Text (with parenthetical) in the middle.",
                "raw_text": "Original raw text",
            },
        ]

        # Act
        result, changed = processor.process(chunks)

        # Assert
        assert len(result) == 3
        assert result[0]["type"] == "dialog"
        assert result[0]["text"] == "Text"
        assert result[1]["type"] == "dialog_modifier"
        assert result[1]["text"] == "(with parenthetical)"
        assert result[2]["type"] == "dialog"
        assert result[2]["text"] == "in the middle."
        assert changed is True

    def test_process_extract_adjacent_parentheticals(self):
        """Test process extracts adjacent parentheticals correctly."""
        # Arrange
        processor = ExtractDialogParentheticalsPreProcessor({})
        chunks = [
            {
                "type": "dialog",
                "speaker": "BOB",
                "text": "Start (pause)(laughs) end.",
                "raw_text": "Original raw text",
            },
        ]

        # Act
        result, changed = processor.process(chunks)

        # Assert
        assert len(result) == 4  # Should be 4 chunks, not 5
        assert result[0]["type"] == "dialog"
        assert result[0]["text"] == "Start"
        assert result[0]["speaker"] == "BOB"

        assert result[1]["type"] == "dialog_modifier"
        assert result[1]["text"] == "(pause)"
        assert result[1]["speaker"] == ""

        assert result[2]["type"] == "dialog_modifier"
        assert result[2]["text"] == "(laughs)"
        assert result[2]["speaker"] == ""

        assert result[3]["type"] == "dialog"
        assert result[3]["text"] == "end."
        assert result[3]["speaker"] == "BOB"

        assert changed is True

    def test_process_extract_multiple_parentheticals_same_chunk(self):
        """Test process extracting multiple parentheticals from the same chunk."""
        # Arrange
        processor = ExtractDialogParentheticalsPreProcessor({})
        chunks = [
            {
                "type": "dialog",
                "speaker": "BOB",
                "text": "First (pause) then (loudly) exclaims.",
                "raw_text": "Original raw text",
            },
        ]

        # Act
        result, changed = processor.process(chunks)

        # Assert
        assert len(result) == 5
        assert result[0]["type"] == "dialog"
        assert result[0]["text"] == "First"
        assert result[1]["type"] == "dialog_modifier"
        assert result[1]["text"] == "(pause)"
        assert result[2]["type"] == "dialog"
        assert result[2]["text"] == "then"
        assert result[3]["type"] == "dialog_modifier"
        assert result[3]["text"] == "(loudly)"
        assert result[4]["type"] == "dialog"
        assert result[4]["text"] == "exclaims."
        assert changed is True

    def test_process_skip_parenthetical_max_words(self):
        """Test process skips parenthetical due to max_words configuration."""
        # Arrange
        processor = ExtractDialogParentheticalsPreProcessor({"max_words": 2})
        chunks = [
            {
                "type": "dialog",
                "speaker": "BOB",
                "text": "Text (with too many words) to skip.",
                "raw_text": "Original raw text",
            },
        ]

        # Act
        result, changed = processor.process(chunks)

        # Assert
        assert result == chunks  # No change
        assert changed is False

    def test_process_extract_pattern_matching(self):
        """Test process extracts only parentheticals matching a pattern."""
        # Arrange
        processor = ExtractDialogParentheticalsPreProcessor(
            {"extract_only": ["pause", "whisper*"]}
        )
        chunks = [
            {
                "type": "dialog",
                "speaker": "BOB",
                "text": "First (pause) then (loudly) then (whispering) ends.",
                "raw_text": "Original raw text",
            },
        ]

        # Act
        result, changed = processor.process(chunks)

        # Assert
        assert len(result) == 5
        assert result[0]["type"] == "dialog"
        assert result[0]["text"] == "First"
        assert result[1]["type"] == "dialog_modifier"
        assert result[1]["text"] == "(pause)"
        assert result[2]["type"] == "dialog"
        assert result[2]["text"] == "then (loudly) then"
        assert result[3]["type"] == "dialog_modifier"
        assert result[3]["text"] == "(whispering)"
        assert result[4]["type"] == "dialog"
        assert result[4]["text"] == "ends."
        assert changed is True

    def test_process_extract_with_complex_scenario(self):
        """Test process with a complex scenario including multiple chunks and parentheticals."""
        # Arrange
        processor = ExtractDialogParentheticalsPreProcessor({})
        chunks = [
            {"type": "action", "text": "Action text"},
            {
                "type": "dialog",
                "speaker": "BOB",
                "text": "Start (pause) middle (loudly) end.",
                "raw_text": "Dialog raw text",
            },
            {"type": "speaker_attribution", "text": "ALICE"},
            {
                "type": "dialog",
                "speaker": "ALICE",
                "text": "Reply (softly).",
                "raw_text": "Reply raw text",
            },
        ]

        # Expected result after processing
        expected = [
            {"type": "action", "text": "Action text"},
            {
                "type": "dialog",
                "speaker": "BOB",
                "text": "Start",
                "raw_text": "Dialog raw text",
            },
            {
                "type": "dialog_modifier",
                "speaker": "",
                "text": "(pause)",
                "raw_text": "Dialog raw text",
            },
            {
                "type": "dialog",
                "speaker": "BOB",
                "text": "middle",
                "raw_text": "Dialog raw text",
            },
            {
                "type": "dialog_modifier",
                "speaker": "",
                "text": "(loudly)",
                "raw_text": "Dialog raw text",
            },
            {
                "type": "dialog",
                "speaker": "BOB",
                "text": "end.",
                "raw_text": "Dialog raw text",
            },
            {"type": "speaker_attribution", "text": "ALICE"},
            {
                "type": "dialog",
                "speaker": "ALICE",
                "text": "Reply",
                "raw_text": "Reply raw text",
            },
            {
                "type": "dialog_modifier",
                "speaker": "",
                "text": "(softly)",
                "raw_text": "Reply raw text",
            },
            {
                "type": "dialog",
                "speaker": "ALICE",
                "text": ".",
                "raw_text": "Reply raw text",
            },
        ]

        # Act
        result, changed = processor.process(chunks)

        # Assert
        assert result == expected
        assert changed is True
