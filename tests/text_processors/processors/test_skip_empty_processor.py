import pytest

from script_to_speech.text_processors.processors.skip_empty_processor import (
    SkipEmptyProcessor,
)


class TestSkipEmptyProcessor:
    """Tests for the SkipEmptyProcessor class."""

    def test_validate_config_valid(self):
        """Test validate_config with valid configuration."""
        # Arrange
        config = {"skip_types": ["page_number", "title"]}
        processor = SkipEmptyProcessor(config)

        # Act & Assert
        assert processor.validate_config() is True

    def test_validate_config_invalid_type(self):
        """Test validate_config with invalid configuration type."""
        # Arrange
        config = {"skip_types": "not_a_list"}
        processor = SkipEmptyProcessor(config)

        # Act & Assert
        assert processor.validate_config() is False

    def test_validate_config_missing_key(self):
        """Test validate_config with missing skip_types key."""
        # Arrange
        config = {"other_key": ["page_number"]}
        processor = SkipEmptyProcessor(config)

        # Act & Assert
        assert processor.validate_config() is False

    def test_get_transformed_fields(self):
        """Test get_transformed_fields returns the correct fields."""
        # Arrange
        processor = SkipEmptyProcessor({})

        # Act
        result = processor.get_transformed_fields()

        # Assert
        assert result == ["text"]

    def test_process_matching_chunk_type(self):
        """Test process with a chunk type that should be emptied."""
        # Arrange
        config = {"skip_types": ["page_number"]}
        processor = SkipEmptyProcessor(config)
        chunk = {"type": "page_number", "text": "Page 42"}

        # Act
        result, changed = processor.process(chunk)

        # Assert
        assert result["text"] == ""
        assert changed is True

    def test_process_non_matching_chunk_type(self):
        """Test process with a chunk type that should not be emptied."""
        # Arrange
        config = {"skip_types": ["page_number"]}
        processor = SkipEmptyProcessor(config)
        chunk = {"type": "dialogue", "text": "Hello world", "speaker": "BOB"}

        # Act
        result, changed = processor.process(chunk)

        # Assert
        assert result == chunk
        assert changed is False

    def test_process_multiple_skip_types(self):
        """Test process with multiple skip types in configuration."""
        # Arrange
        config = {"skip_types": ["page_number", "title"]}
        processor = SkipEmptyProcessor(config)

        # Test with first skip type
        chunk1 = {"type": "page_number", "text": "Page 42"}

        # Test with second skip type
        chunk2 = {"type": "title", "text": "My Screenplay"}

        # Test with non-skip type
        chunk3 = {"type": "action", "text": "Bob walks in"}

        # Act
        result1, changed1 = processor.process(chunk1)
        result2, changed2 = processor.process(chunk2)
        result3, changed3 = processor.process(chunk3)

        # Assert
        assert result1["text"] == ""
        assert changed1 is True

        assert result2["text"] == ""
        assert changed2 is True

        assert result3["text"] == "Bob walks in"
        assert changed3 is False

    def test_process_preserves_other_fields(self):
        """Test that process only changes text field, preserving others."""
        # Arrange
        config = {"skip_types": ["page_number"]}
        processor = SkipEmptyProcessor(config)
        chunk = {
            "type": "page_number",
            "text": "Page 42",
            "raw_text": "Original raw text",
            "speaker": "NARRATOR",
            "custom_field": "Some value",
        }

        # Act
        result, changed = processor.process(chunk)

        # Assert
        assert result["text"] == ""
        assert result["type"] == "page_number"
        assert result["raw_text"] == "Original raw text"
        assert result["speaker"] == "NARRATOR"
        assert result["custom_field"] == "Some value"
        assert changed is True

    def test_process_empty_config(self):
        """Test process with empty skip_types configuration."""
        # Arrange
        config = {"skip_types": []}
        processor = SkipEmptyProcessor(config)
        chunk = {"type": "page_number", "text": "Page 42"}

        # Act
        result, changed = processor.process(chunk)

        # Assert
        assert result == chunk
        assert changed is False

    def test_process_already_empty_text(self):
        """Test process with already empty text field."""
        # Arrange
        config = {"skip_types": ["page_number"]}
        processor = SkipEmptyProcessor(config)
        chunk = {"type": "page_number", "text": ""}

        # Act
        result, changed = processor.process(chunk)

        # Assert
        assert result["text"] == ""
        assert changed is False  # No change occurred since text was already empty

    def test_processor_state_isolation(self):
        """Test that the processor doesn't maintain state between process calls."""
        # Arrange
        config = {"skip_types": ["page_number"]}
        processor = SkipEmptyProcessor(config)

        # Chunks to process
        chunk1 = {"type": "page_number", "text": "42"}
        chunk2 = {"type": "scene_heading", "text": "INT. HOUSE - DAY"}

        # Act
        result1, _ = processor.process(chunk1)
        result2, _ = processor.process(chunk2)
        result1_repeat, _ = processor.process(chunk1)

        # Assert
        assert result1["text"] == ""  # Text should be emptied
        assert result2["text"] == "INT. HOUSE - DAY"  # Should remain unchanged
        assert result1_repeat["text"] == ""  # Should match first processing
