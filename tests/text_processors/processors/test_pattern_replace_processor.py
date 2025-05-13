import pytest

from script_to_speech.text_processors.processors.pattern_replace_processor import (
    PatternReplaceProcessor,
)


class TestPatternReplaceProcessor:
    """Tests for the PatternReplaceProcessor class."""

    def test_validate_config_valid(self):
        """Test validate_config with valid configuration."""
        # Arrange
        config = {
            "replacements": [
                {
                    "match_field": "type",
                    "match_pattern": "^dialogue_modifier$",
                    "replace_field": "speaker",
                    "replace_pattern": ".*",
                    "replace_string": "",
                }
            ]
        }
        processor = PatternReplaceProcessor(config)

        # Act & Assert
        assert processor.validate_config() is True

    def test_validate_config_invalid_not_list(self):
        """Test validate_config with invalid configuration (not a list)."""
        # Arrange
        config = {"replacements": "not_a_list"}
        processor = PatternReplaceProcessor(config)

        # Act & Assert
        assert processor.validate_config() is False

    def test_validate_config_invalid_missing_keys(self):
        """Test validate_config with invalid configuration (missing required keys)."""
        # Arrange - Missing match_field
        config = {
            "replacements": [
                {
                    "match_pattern": "^dialogue_modifier$",
                    "replace_field": "speaker",
                    "replace_pattern": ".*",
                    "replace_string": "",
                }
            ]
        }
        processor = PatternReplaceProcessor(config)

        # Act & Assert
        assert processor.validate_config() is False

        # Arrange - Missing match_pattern
        config = {
            "replacements": [
                {
                    "match_field": "type",
                    "replace_field": "speaker",
                    "replace_pattern": ".*",
                    "replace_string": "",
                }
            ]
        }
        processor = PatternReplaceProcessor(config)

        # Act & Assert
        assert processor.validate_config() is False

    def test_validate_config_invalid_values_not_strings(self):
        """Test validate_config with invalid configuration (values not strings)."""
        # Arrange
        config = {
            "replacements": [
                {
                    "match_field": "type",
                    "match_pattern": 123,  # Should be string
                    "replace_field": "speaker",
                    "replace_pattern": ".*",
                    "replace_string": "",
                }
            ]
        }
        processor = PatternReplaceProcessor(config)

        # Act & Assert
        assert processor.validate_config() is False

    def test_validate_config_invalid_regex(self):
        """Test validate_config with invalid regex patterns."""
        # Arrange - Invalid match_pattern
        config = {
            "replacements": [
                {
                    "match_field": "type",
                    "match_pattern": "[",  # Invalid regex
                    "replace_field": "speaker",
                    "replace_pattern": ".*",
                    "replace_string": "",
                }
            ]
        }
        processor = PatternReplaceProcessor(config)

        # Act & Assert
        assert processor.validate_config() is False

        # Arrange - Invalid replace_pattern
        config = {
            "replacements": [
                {
                    "match_field": "type",
                    "match_pattern": ".*",
                    "replace_field": "speaker",
                    "replace_pattern": "(",  # Invalid regex
                    "replace_string": "",
                }
            ]
        }
        processor = PatternReplaceProcessor(config)

        # Act & Assert
        assert processor.validate_config() is False

    def test_get_transformed_fields(self):
        """Test get_transformed_fields returns correct fields."""
        # Arrange
        config = {
            "replacements": [
                {
                    "match_field": "type",
                    "match_pattern": "^dialogue_modifier$",
                    "replace_field": "speaker",
                    "replace_pattern": ".*",
                    "replace_string": "",
                },
                {
                    "match_field": "type",
                    "match_pattern": "^scene_heading$",
                    "replace_field": "text",
                    "replace_pattern": "INT\\.",
                    "replace_string": "INTERIOR",
                },
            ]
        }
        processor = PatternReplaceProcessor(config)

        # Act
        result = processor.get_transformed_fields()

        # Assert
        assert sorted(result) == sorted(["speaker", "text"])

    def test_process_match_replace_exact_pattern(self):
        """Test process with a simple pattern match and replacement."""
        # Arrange
        config = {
            "replacements": [
                {
                    "match_field": "type",
                    "match_pattern": "^dialogue_modifier$",
                    "replace_field": "speaker",
                    "replace_pattern": ".*",
                    "replace_string": "",
                }
            ]
        }
        processor = PatternReplaceProcessor(config)

        # This chunk should match and be modified
        chunk = {"type": "dialogue_modifier", "speaker": "BOB", "text": "(quietly)"}

        # Act
        result, changed = processor.process(chunk)

        # Assert
        assert result["speaker"] == ""
        assert changed is True

    def test_process_match_but_no_replace_field(self):
        """Test process when match field matches but replace field doesn't exist."""
        # Arrange
        config = {
            "replacements": [
                {
                    "match_field": "type",
                    "match_pattern": "^dialogue_modifier$",
                    "replace_field": "nonexistent_field",
                    "replace_pattern": ".*",
                    "replace_string": "",
                }
            ]
        }
        processor = PatternReplaceProcessor(config)

        chunk = {"type": "dialogue_modifier", "speaker": "BOB", "text": "(quietly)"}

        # Act
        result, changed = processor.process(chunk)

        # Assert - No change should occur
        assert result == chunk
        assert changed is False

    def test_process_no_match(self):
        """Test process when match field doesn't match pattern."""
        # Arrange
        config = {
            "replacements": [
                {
                    "match_field": "type",
                    "match_pattern": "^dialogue_modifier$",
                    "replace_field": "speaker",
                    "replace_pattern": ".*",
                    "replace_string": "",
                }
            ]
        }
        processor = PatternReplaceProcessor(config)

        # This chunk should not match
        chunk = {"type": "dialogue", "speaker": "BOB", "text": "Hello world"}

        # Act
        result, changed = processor.process(chunk)

        # Assert
        assert result == chunk
        assert changed is False

    def test_process_match_field_not_in_chunk(self):
        """Test process when match field isn't in the chunk."""
        # Arrange
        config = {
            "replacements": [
                {
                    "match_field": "nonexistent_field",
                    "match_pattern": ".*",
                    "replace_field": "text",
                    "replace_pattern": "hello",
                    "replace_string": "goodbye",
                }
            ]
        }
        processor = PatternReplaceProcessor(config)

        chunk = {"type": "dialogue", "speaker": "BOB", "text": "Hello world"}

        # Act
        result, changed = processor.process(chunk)

        # Assert - No change should occur
        assert result == chunk
        assert changed is False

    def test_process_multiple_replacements(self):
        """Test process with multiple replacement patterns."""
        # Arrange
        config = {
            "replacements": [
                {
                    "match_field": "type",
                    "match_pattern": "^dialogue_modifier$",
                    "replace_field": "speaker",
                    "replace_pattern": ".*",
                    "replace_string": "",
                },
                {
                    "match_field": "type",
                    "match_pattern": "^dialogue_modifier$",
                    "replace_field": "text",
                    "replace_pattern": "^\\((.*)\\)$",
                    "replace_string": "\\1",
                },
            ]
        }
        processor = PatternReplaceProcessor(config)

        chunk = {"type": "dialogue_modifier", "speaker": "BOB", "text": "(quietly)"}

        # Act
        result, changed = processor.process(chunk)

        # Assert - Both replacements should apply
        assert result["speaker"] == ""
        assert result["text"] == "quietly"
        assert changed is True

    def test_process_capture_groups(self):
        """Test process with capture groups in the replacement pattern."""
        # Arrange
        config = {
            "replacements": [
                {
                    "match_field": "type",
                    "match_pattern": "^scene_heading$",
                    "replace_field": "text",
                    "replace_pattern": "^(?P<scene_num>[A-Z]?\\d+(\\.\\d+)?)(.*)((?P=scene_num))$",
                    "replace_string": "\\1\\3",
                }
            ]
        }
        processor = PatternReplaceProcessor(config)

        chunk = {"type": "scene_heading", "text": "22 INT. HEADQUARTERS -- NIGHT 22"}

        # Act
        result, changed = processor.process(chunk)

        # Assert
        assert result["text"] == "22 INT. HEADQUARTERS -- NIGHT "
        assert changed is True

    def test_process_case_sensitive_matching(self):
        """Test process with case-sensitive pattern matching."""
        # Arrange
        config = {
            "replacements": [
                {
                    "match_field": "text",
                    "match_pattern": "Hello",  # Case-sensitive pattern
                    "replace_field": "text",
                    "replace_pattern": "Hello",
                    "replace_string": "Goodbye",
                }
            ]
        }
        processor = PatternReplaceProcessor(config)

        # This should match
        chunk1 = {"type": "dialogue", "text": "Hello world"}

        # This should not match (different case)
        chunk2 = {"type": "dialogue", "text": "hello world"}

        # Act
        result1, changed1 = processor.process(chunk1)
        result2, changed2 = processor.process(chunk2)

        # Assert
        assert result1["text"] == "Goodbye world"
        assert changed1 is True

        assert result2["text"] == "hello world"
        assert changed2 is False

    def test_process_case_insensitive_matching(self):
        """Test process with case-insensitive pattern matching."""
        # Arrange
        config = {
            "replacements": [
                {
                    "match_field": "text",
                    "match_pattern": "(?i)hello",  # Case-insensitive pattern
                    "replace_field": "text",
                    "replace_pattern": "(?i)hello",
                    "replace_string": "Goodbye",
                }
            ]
        }
        processor = PatternReplaceProcessor(config)

        # Both should match
        chunk1 = {"type": "dialogue", "text": "Hello world"}

        chunk2 = {"type": "dialogue", "text": "hello world"}

        # Act
        result1, changed1 = processor.process(chunk1)
        result2, changed2 = processor.process(chunk2)

        # Assert
        assert result1["text"] == "Goodbye world"
        assert changed1 is True

        assert result2["text"] == "Goodbye world"
        assert changed2 is True

    def test_process_empty_replace_string(self):
        """Test process with empty replacement string (deletion)."""
        # Arrange
        config = {
            "replacements": [
                {
                    "match_field": "type",
                    "match_pattern": "^dialogue_modifier$",
                    "replace_field": "text",
                    "replace_pattern": "\\(|\\)",  # Match opening or closing parenthesis
                    "replace_string": "",
                }
            ]
        }
        processor = PatternReplaceProcessor(config)

        chunk = {"type": "dialogue_modifier", "text": "(softly)"}

        # Act
        result, changed = processor.process(chunk)

        # Assert - Parentheses should be removed
        assert result["text"] == "softly"
        assert changed is True

    def test_processor_state_isolation(self):
        """Test that the processor doesn't maintain state between process calls."""
        # Arrange
        config = {
            "replacements": [
                {
                    "match_field": "type",
                    "match_pattern": "^dialogue_modifier$",
                    "replace_field": "text",
                    "replace_pattern": "\\(|\\)",
                    "replace_string": "",
                }
            ]
        }
        processor = PatternReplaceProcessor(config)

        # Chunks to process
        chunk1 = {"type": "dialogue_modifier", "text": "(quietly)"}
        chunk2 = {"type": "dialogue_modifier", "text": "(loudly)"}

        # Act
        result1, _ = processor.process(chunk1)
        result2, _ = processor.process(chunk2)
        result1_repeat, _ = processor.process(chunk1)

        # Assert
        assert result1["text"] == "quietly"
        assert result2["text"] == "loudly"
        assert result1_repeat["text"] == "quietly"  # Should match first processing
