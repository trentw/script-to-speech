import pytest

from script_to_speech.text_processors.processors.text_substitution_processor import (
    TextSubstitutionProcessor,
)


class TestTextSubstitutionProcessor:
    """Tests for the TextSubstitutionProcessor class."""

    def test_validate_config_valid(self):
        """Test validate_config with valid configuration."""
        # Arrange
        config = {
            "substitutions": [{"from": "INT.", "to": "INTERIOR", "fields": ["text"]}]
        }
        processor = TextSubstitutionProcessor(config)

        # Act & Assert
        assert processor.validate_config() is True

    def test_validate_config_invalid_not_list(self):
        """Test validate_config with invalid configuration (not a list)."""
        # Arrange
        config = {"substitutions": "not_a_list"}
        processor = TextSubstitutionProcessor(config)

        # Act & Assert
        assert processor.validate_config() is False

    def test_validate_config_invalid_missing_keys(self):
        """Test validate_config with invalid configuration (missing keys)."""
        # Arrange - Missing 'to' key
        config = {"substitutions": [{"from": "INT.", "fields": ["text"]}]}
        processor = TextSubstitutionProcessor(config)

        # Act & Assert
        assert processor.validate_config() is False

        # Arrange - Missing 'from' key
        config = {"substitutions": [{"to": "INTERIOR", "fields": ["text"]}]}
        processor = TextSubstitutionProcessor(config)

        # Act & Assert
        assert processor.validate_config() is False

        # Arrange - Missing 'fields' key
        config = {"substitutions": [{"from": "INT.", "to": "INTERIOR"}]}
        processor = TextSubstitutionProcessor(config)

        # Act & Assert
        assert processor.validate_config() is False

    def test_validate_config_invalid_fields_not_list(self):
        """Test validate_config with invalid configuration (fields not a list)."""
        # Arrange
        config = {
            "substitutions": [
                {"from": "INT.", "to": "INTERIOR", "fields": "text"}  # Should be a list
            ]
        }
        processor = TextSubstitutionProcessor(config)

        # Act & Assert
        assert processor.validate_config() is False

    def test_get_transformed_fields(self):
        """Test get_transformed_fields returns correct fields from substitutions."""
        # Arrange
        config = {
            "substitutions": [
                {"from": "INT.", "to": "INTERIOR", "fields": ["text"]},
                {"from": "EXT.", "to": "EXTERIOR", "fields": ["text", "raw_text"]},
            ]
        }
        processor = TextSubstitutionProcessor(config)

        # Act
        transformed_fields = processor.get_transformed_fields()

        # Assert
        assert sorted(transformed_fields) == sorted(["text", "raw_text"])

    def test_process_single_substitution(self):
        """Test process with a single substitution."""
        # Arrange
        config = {
            "substitutions": [{"from": "INT.", "to": "INTERIOR", "fields": ["text"]}]
        }
        processor = TextSubstitutionProcessor(config)
        chunk = {"type": "scene_heading", "text": "INT. BEDROOM - DAY"}

        # Act
        result, changed = processor.process(chunk)

        # Assert
        assert result["text"] == "INTERIOR BEDROOM - DAY"
        assert changed is True

    def test_process_multiple_substitutions(self):
        """Test process with multiple substitutions."""
        # Arrange
        config = {
            "substitutions": [
                {"from": "INT.", "to": "INTERIOR", "fields": ["text"]},
                {"from": "EXT.", "to": "EXTERIOR", "fields": ["text"]},
            ]
        }
        processor = TextSubstitutionProcessor(config)

        # Test first substitution
        chunk1 = {"type": "scene_heading", "text": "INT. BEDROOM - DAY"}

        # Test second substitution
        chunk2 = {"type": "scene_heading", "text": "EXT. PARK - NIGHT"}

        # Act
        result1, changed1 = processor.process(chunk1)
        result2, changed2 = processor.process(chunk2)

        # Assert
        assert result1["text"] == "INTERIOR BEDROOM - DAY"
        assert changed1 is True

        assert result2["text"] == "EXTERIOR PARK - NIGHT"
        assert changed2 is True

    def test_process_multiple_fields(self):
        """Test process with substitutions in multiple fields."""
        # Arrange
        config = {
            "substitutions": [
                {"from": "INT.", "to": "INTERIOR", "fields": ["text", "raw_text"]}
            ]
        }
        processor = TextSubstitutionProcessor(config)
        chunk = {
            "type": "scene_heading",
            "text": "INT. BEDROOM - DAY",
            "raw_text": "INT. BEDROOM - DAY - ORIGINAL",
        }

        # Act
        result, changed = processor.process(chunk)

        # Assert
        assert result["text"] == "INTERIOR BEDROOM - DAY"
        assert result["raw_text"] == "INTERIOR BEDROOM - DAY - ORIGINAL"
        assert changed is True

    def test_process_no_changes(self):
        """Test process with no matching substitutions."""
        # Arrange
        config = {
            "substitutions": [{"from": "INT.", "to": "INTERIOR", "fields": ["text"]}]
        }
        processor = TextSubstitutionProcessor(config)
        chunk = {"type": "scene_heading", "text": "EXTERIOR PARK - NIGHT"}

        # Act
        result, changed = processor.process(chunk)

        # Assert
        assert result == chunk
        assert changed is False

    def test_process_field_not_in_chunk(self):
        """Test process with a field that doesn't exist in the chunk."""
        # Arrange
        config = {
            "substitutions": [
                {
                    "from": "INT.",
                    "to": "INTERIOR",
                    "fields": ["text", "nonexistent_field"],
                }
            ]
        }
        processor = TextSubstitutionProcessor(config)
        chunk = {"type": "scene_heading", "text": "INT. BEDROOM - DAY"}

        # Act
        result, changed = processor.process(chunk)

        # Assert - Should still process existing fields
        assert result["text"] == "INTERIOR BEDROOM - DAY"
        assert changed is True
        # No error from nonexistent field

    def test_process_special_regex_characters(self):
        """Test process with text containing special regex characters."""
        # Arrange
        config = {
            "substitutions": [
                {"from": "(V.O.)", "to": "(VOICE OVER)", "fields": ["text"]},
                {
                    "from": "$5.99",
                    "to": "five dollars and ninety-nine cents",
                    "fields": ["text"],
                },
            ]
        }
        processor = TextSubstitutionProcessor(config)

        # Special characters like parentheses should be handled properly
        chunk1 = {"type": "speaker_attribution", "text": "BOB (V.O.)"}

        # Special characters like dollar signs should be handled properly
        chunk2 = {"type": "dialogue", "text": "That costs $5.99"}

        # Act
        result1, changed1 = processor.process(chunk1)
        result2, changed2 = processor.process(chunk2)

        # Assert
        assert result1["text"] == "BOB (VOICE OVER)"
        assert changed1 is True

        assert result2["text"] == "That costs five dollars and ninety-nine cents"
        assert changed2 is True

    def test_process_multiple_occurrences(self):
        """Test process with multiple occurrences of the same pattern."""
        # Arrange
        config = {
            "substitutions": [{"from": "INT.", "to": "INTERIOR", "fields": ["text"]}]
        }
        processor = TextSubstitutionProcessor(config)
        chunk = {"type": "scene_heading", "text": "INT. BEDROOM - INT. KITCHEN"}

        # Act
        result, changed = processor.process(chunk)

        # Assert - Both occurrences should be replaced
        assert result["text"] == "INTERIOR BEDROOM - INTERIOR KITCHEN"
        assert changed is True

    def test_processor_state_isolation(self):
        """Test that the processor doesn't maintain state between process calls."""
        # Arrange
        config = {
            "substitutions": [{"from": "INT.", "to": "INTERIOR", "fields": ["text"]}]
        }
        processor = TextSubstitutionProcessor(config)

        # Chunks to process
        chunk1 = {"type": "scene_heading", "text": "INT. BEDROOM - DAY"}
        chunk2 = {"type": "scene_heading", "text": "INT. KITCHEN - NIGHT"}

        # Act
        result1, _ = processor.process(chunk1)
        result2, _ = processor.process(chunk2)
        result1_repeat, _ = processor.process(chunk1)

        # Assert
        assert result1["text"] == "INTERIOR BEDROOM - DAY"
        assert result2["text"] == "INTERIOR KITCHEN - NIGHT"
        assert (
            result1_repeat["text"] == "INTERIOR BEDROOM - DAY"
        )  # Should match first processing
