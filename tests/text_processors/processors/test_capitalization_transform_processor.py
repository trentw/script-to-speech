import re

import pytest

from script_to_speech.text_processors.processors.capitalization_transform_processor import (
    CapitalizationTransformProcessor,
)


class TestCapitalizationTransformProcessor:
    """Tests for the CapitalizationTransformProcessor class."""

    def test_validate_config_valid(self):
        """Test validate_config with valid configuration."""
        # Arrange
        config = {
            "transformations": [
                {"chunk_type": "speaker_attribution", "case": "sentence_case"},
                {"chunk_type": "dialog_modifier", "case": "lower_case"},
            ]
        }
        processor = CapitalizationTransformProcessor(config)

        # Act & Assert
        assert processor.validate_config() is True

    def test_validate_config_invalid_not_list(self):
        """Test validate_config with invalid configuration (not a list)."""
        # Arrange
        config = {"transformations": "not_a_list"}
        processor = CapitalizationTransformProcessor(config)

        # Act & Assert
        assert processor.validate_config() is False

    def test_validate_config_invalid_missing_required_fields(self):
        """Test validate_config with invalid configuration (missing required fields)."""
        # Arrange - Missing chunk_type
        config = {"transformations": [{"case": "sentence_case"}]}
        processor = CapitalizationTransformProcessor(config)

        # Act & Assert
        assert processor.validate_config() is False

        # Arrange - Missing case
        config = {"transformations": [{"chunk_type": "speaker_attribution"}]}
        processor = CapitalizationTransformProcessor(config)

        # Act & Assert
        assert processor.validate_config() is False

    def test_validate_config_invalid_case_type(self):
        """Test validate_config with invalid case type."""
        # Arrange
        config = {
            "transformations": [
                {
                    "chunk_type": "speaker_attribution",
                    "case": "invalid_case",  # Not a valid case type
                }
            ]
        }
        processor = CapitalizationTransformProcessor(config)

        # Act & Assert
        assert processor.validate_config() is False

    def test_validate_config_invalid_regex_pattern(self):
        """Test validate_config with invalid regex pattern."""
        # Arrange
        config = {
            "transformations": [
                {
                    "chunk_type": "speaker_attribution",
                    "case": "sentence_case",
                    "text_must_contain_pattern": "[",  # Invalid regex
                }
            ]
        }
        processor = CapitalizationTransformProcessor(config)

        # Act & Assert
        assert processor.validate_config() is False

    def test_get_transformed_fields(self):
        """Test get_transformed_fields returns the correct fields."""
        # Arrange
        processor = CapitalizationTransformProcessor({})

        # Act
        result = processor.get_transformed_fields()

        # Assert
        assert result == ["text"]

    def test_transform_case_upper_case(self):
        """Test _transform_case with upper_case transformation."""
        # Arrange
        processor = CapitalizationTransformProcessor({})
        text = "hello world"

        # Act
        result = processor._transform_case(text, "upper_case")

        # Assert
        assert result == "HELLO WORLD"

    def test_transform_case_lower_case(self):
        """Test _transform_case with lower_case transformation."""
        # Arrange
        processor = CapitalizationTransformProcessor({})
        text = "HELLO WORLD"

        # Act
        result = processor._transform_case(text, "lower_case")

        # Assert
        assert result == "hello world"

    def test_transform_case_sentence_case(self):
        """Test _transform_case with sentence_case transformation."""
        # Arrange
        processor = CapitalizationTransformProcessor({})
        text = "hello world"

        # Act
        result = processor._transform_case(text, "sentence_case")

        # Assert
        assert result == "Hello world"

    def test_transform_case_invalid_case(self):
        """Test _transform_case with invalid case type defaults to no change."""
        # Arrange
        processor = CapitalizationTransformProcessor({})
        text = "hello world"

        # Act
        result = processor._transform_case(text, "invalid_case")

        # Assert
        assert result == "hello world"  # No change

    def test_process_matching_chunk_type(self):
        """Test process with a matching chunk type."""
        # Arrange
        config = {
            "transformations": [
                {"chunk_type": "speaker_attribution", "case": "sentence_case"}
            ]
        }
        processor = CapitalizationTransformProcessor(config)
        chunk = {"type": "speaker_attribution", "text": "BOB SMITH"}

        # Act
        result, changed = processor.process(chunk)

        # Assert
        assert result["text"] == "Bob smith"
        assert changed is True

    def test_process_non_matching_chunk_type(self):
        """Test process with a non-matching chunk type."""
        # Arrange
        config = {
            "transformations": [
                {"chunk_type": "speaker_attribution", "case": "sentence_case"}
            ]
        }
        processor = CapitalizationTransformProcessor(config)
        chunk = {"type": "dialog", "text": "BOB SMITH"}  # Different from config

        # Act
        result, changed = processor.process(chunk)

        # Assert
        assert result["text"] == "BOB SMITH"  # No change
        assert changed is False

    def test_process_multiple_transformations(self):
        """Test process with multiple transformations."""
        # Arrange
        config = {
            "transformations": [
                {"chunk_type": "speaker_attribution", "case": "sentence_case"},
                {"chunk_type": "dialog_modifier", "case": "lower_case"},
            ]
        }
        processor = CapitalizationTransformProcessor(config)

        # Test first transformation
        chunk1 = {"type": "speaker_attribution", "text": "BOB SMITH"}

        # Test second transformation
        chunk2 = {"type": "dialog_modifier", "text": "QUIETLY WHISPERS"}

        # Act
        result1, changed1 = processor.process(chunk1)
        result2, changed2 = processor.process(chunk2)

        # Assert
        assert result1["text"] == "Bob smith"
        assert changed1 is True

        assert result2["text"] == "quietly whispers"
        assert changed2 is True

    def test_process_with_text_must_contain_string(self):
        """Test process with text_must_contain_string condition."""
        # Arrange
        config = {
            "transformations": [
                {
                    "chunk_type": "dialog",
                    "case": "lower_case",
                    "text_must_contain_string": "IMPORTANT",
                }
            ]
        }
        processor = CapitalizationTransformProcessor(config)

        # Should match and transform
        chunk1 = {"type": "dialog", "text": "THIS IS IMPORTANT TEXT"}

        # Should not match or transform
        chunk2 = {"type": "dialog", "text": "THIS IS REGULAR TEXT"}

        # Act
        result1, changed1 = processor.process(chunk1)
        result2, changed2 = processor.process(chunk2)

        # Assert
        assert result1["text"] == "this is important text"
        assert changed1 is True

        assert result2["text"] == "THIS IS REGULAR TEXT"  # No change
        assert changed2 is False

    def test_process_with_text_must_contain_pattern(self):
        """Test process with text_must_contain_pattern condition."""
        # Arrange
        config = {
            "transformations": [
                {
                    "chunk_type": "dialog",
                    "case": "lower_case",
                    "text_must_contain_pattern": "\\d+",  # Contains digits
                }
            ]
        }
        processor = CapitalizationTransformProcessor(config)

        # Should match and transform (contains digits)
        chunk1 = {"type": "dialog", "text": "CALL ME AT 555-1234"}

        # Should not match or transform (no digits)
        chunk2 = {"type": "dialog", "text": "CALL ME LATER"}

        # Act
        result1, changed1 = processor.process(chunk1)
        result2, changed2 = processor.process(chunk2)

        # Assert
        assert result1["text"] == "call me at 555-1234"
        assert changed1 is True

        assert result2["text"] == "CALL ME LATER"  # No change
        assert changed2 is False

    def test_process_with_both_conditions(self):
        """Test process with both text_must_contain_string and text_must_contain_pattern."""
        # Arrange
        config = {
            "transformations": [
                {
                    "chunk_type": "dialog",
                    "case": "lower_case",
                    "text_must_contain_string": "CALL",
                    "text_must_contain_pattern": "\\d+",  # Contains digits
                }
            ]
        }
        processor = CapitalizationTransformProcessor(config)

        # Should match and transform (contains "CALL" and digits)
        chunk1 = {"type": "dialog", "text": "CALL ME AT 555-1234"}

        # Should not match (contains "CALL" but no digits)
        chunk2 = {"type": "dialog", "text": "CALL ME LATER"}

        # Should not match (contains digits but not "CALL")
        chunk3 = {"type": "dialog", "text": "MY NUMBER IS 555-1234"}

        # Act
        result1, changed1 = processor.process(chunk1)
        result2, changed2 = processor.process(chunk2)
        result3, changed3 = processor.process(chunk3)

        # Assert
        assert result1["text"] == "call me at 555-1234"
        assert changed1 is True

        assert result2["text"] == "CALL ME LATER"  # No change
        assert changed2 is False

        assert result3["text"] == "MY NUMBER IS 555-1234"  # No change
        assert changed3 is False

    def test_process_multiple_sequential_transformations(self):
        """Test that process can apply multiple transformations to the same chunk sequentially."""
        # Arrange - First lowercase, then if contains "important", sentence case
        config = {
            "transformations": [
                {"chunk_type": "dialog", "case": "lower_case"},
                {
                    "chunk_type": "dialog",
                    "case": "sentence_case",
                    "text_must_contain_string": "important",
                },
            ]
        }
        processor = CapitalizationTransformProcessor(config)

        chunk = {"type": "dialog", "text": "THIS IS IMPORTANT TEXT"}

        # Act
        result, changed = processor.process(chunk)

        # Assert - Should first lowercase everything, then sentence case because it contains "important"
        assert result["text"] == "This is important text"
        assert changed is True

    def test_processor_state_isolation(self):
        """Test that the processor doesn't maintain state between process calls."""
        # Arrange
        config = {"transformations": [{"chunk_type": "dialog", "case": "lower_case"}]}
        processor = CapitalizationTransformProcessor(config)

        # First chunk to process
        chunk1 = {"type": "dialog", "text": "HELLO WORLD"}

        # Second chunk with different content
        chunk2 = {"type": "dialog", "text": "TESTING STATE"}

        # Act
        result1, _ = processor.process(chunk1)
        result2, _ = processor.process(chunk2)
        result1_repeat, _ = processor.process(chunk1)

        # Assert
        assert result1["text"] == "hello world"
        assert result2["text"] == "testing state"
        assert result1_repeat["text"] == "hello world"  # Should match first processing
