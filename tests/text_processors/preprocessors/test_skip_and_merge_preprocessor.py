import pytest

from script_to_speech.text_processors.preprocessors.skip_and_merge_preprocessor import (
    SkipAndMergePreProcessor,
)


class TestSkipAndMergePreProcessor:
    """Tests for the SkipAndMergePreProcessor class."""

    def test_validate_config_valid(self):
        """Test validate_config with valid configuration."""
        # Arrange
        config = {"skip_types": ["page_number", "title"]}
        processor = SkipAndMergePreProcessor(config)

        # Act & Assert
        assert processor.validate_config() is True

    def test_validate_config_invalid(self):
        """Test validate_config with invalid configuration."""
        # Arrange
        config = {"skip_types": "not_a_list"}
        processor = SkipAndMergePreProcessor(config)

        # Act & Assert
        assert processor.validate_config() is False

    def test_can_merge_chunks_same_type_mergeable(self):
        """Test _can_merge_chunks with same type and mergeable type."""
        # Arrange
        processor = SkipAndMergePreProcessor({"skip_types": []})
        chunk1 = {"type": "action", "text": "Text 1"}
        chunk2 = {"type": "action", "text": "Text 2"}

        # Act
        result = processor._can_merge_chunks(chunk1, chunk2)

        # Assert
        assert result is True

    def test_can_merge_chunks_different_type(self):
        """Test _can_merge_chunks with different types."""
        # Arrange
        processor = SkipAndMergePreProcessor({"skip_types": []})
        chunk1 = {"type": "action", "text": "Text 1"}
        chunk2 = {"type": "dialogue", "text": "Text 2"}

        # Act
        result = processor._can_merge_chunks(chunk1, chunk2)

        # Assert
        assert result is False

    def test_can_merge_chunks_not_mergeable_type(self):
        """Test _can_merge_chunks with non-mergeable type."""
        # Arrange
        processor = SkipAndMergePreProcessor({"skip_types": []})
        chunk1 = {"type": "title", "text": "Text 1"}
        chunk2 = {"type": "title", "text": "Text 2"}

        # Act
        result = processor._can_merge_chunks(chunk1, chunk2)

        # Assert
        assert result is False

    def test_can_merge_chunks_dialogue_same_speaker(self):
        """Test _can_merge_chunks with dialogue chunks having the same speaker."""
        # Arrange
        processor = SkipAndMergePreProcessor({"skip_types": []})
        chunk1 = {"type": "dialogue", "speaker": "BOB", "text": "Text 1"}
        chunk2 = {"type": "dialogue", "speaker": "BOB", "text": "Text 2"}

        # Act
        result = processor._can_merge_chunks(chunk1, chunk2)

        # Assert
        assert result is True

    def test_can_merge_chunks_dialogue_different_speaker(self):
        """Test _can_merge_chunks with dialogue chunks having different speakers."""
        # Arrange
        processor = SkipAndMergePreProcessor({"skip_types": []})
        chunk1 = {"type": "dialogue", "speaker": "BOB", "text": "Text 1"}
        chunk2 = {"type": "dialogue", "speaker": "ALICE", "text": "Text 2"}

        # Act
        result = processor._can_merge_chunks(chunk1, chunk2)

        # Assert
        assert result is False

    def test_merge_chunks(self):
        """Test _merge_chunks combines two chunks correctly."""
        # Arrange
        processor = SkipAndMergePreProcessor({"skip_types": []})
        chunk1 = {"type": "action", "text": "Text 1", "raw_text": "Raw text 1"}
        chunk2 = {"type": "action", "text": "Text 2", "raw_text": "Raw text 2"}

        # Act
        result = processor._merge_chunks(chunk1, chunk2)

        # Assert
        assert result["type"] == "action"
        assert result["text"] == "Text 1 Text 2"
        assert result["raw_text"] == "Raw text 1\nRaw text 2"

    def test_process_empty_list(self):
        """Test process with empty chunks list."""
        # Arrange
        processor = SkipAndMergePreProcessor({"skip_types": ["page_number"]})

        # Act
        result, changed = processor.process([])

        # Assert
        assert result == []
        assert changed is False

    def test_process_no_skipped_types(self):
        """Test process with no chunks to skip."""
        # Arrange
        processor = SkipAndMergePreProcessor({"skip_types": ["page_number"]})
        chunks = [
            {"type": "action", "text": "Action 1"},
            {"type": "dialogue", "speaker": "BOB", "text": "Dialogue 1"},
        ]

        # Act
        result, changed = processor.process(chunks)

        # Assert
        assert result == chunks
        assert changed is False

    def test_process_skip_chunk(self):
        """Test process skips chunks of specified types."""
        # Arrange
        processor = SkipAndMergePreProcessor({"skip_types": ["page_number"]})
        chunks = [
            {"type": "action", "text": "Action 1"},
            {"type": "page_number", "text": "1"},
            {"type": "dialogue", "speaker": "BOB", "text": "Dialogue 1"},
        ]

        # Act
        result, changed = processor.process(chunks)

        # Assert
        assert len(result) == 2
        assert result[0]["type"] == "action"
        assert result[1]["type"] == "dialogue"
        assert changed is True

    def test_process_merge_around_skipped(self):
        """Test process merges chunks around skipped chunk."""
        # Arrange
        processor = SkipAndMergePreProcessor({"skip_types": ["page_number"]})
        chunks = [
            {"type": "action", "text": "Action 1", "raw_text": "Raw action 1"},
            {"type": "page_number", "text": "1", "raw_text": "1"},
            {"type": "action", "text": "Action 2", "raw_text": "Raw action 2"},
        ]

        # Act
        result, changed = processor.process(chunks)

        # Assert
        assert len(result) == 1
        assert result[0]["type"] == "action"
        assert result[0]["text"] == "Action 1 Action 2"
        assert result[0]["raw_text"] == "Raw action 1\nRaw action 2"
        assert changed is True

    def test_process_no_merge_different_types(self):
        """Test process doesn't merge different types around skipped chunk."""
        # Arrange
        processor = SkipAndMergePreProcessor({"skip_types": ["page_number"]})
        chunks = [
            {"type": "action", "text": "Action 1"},
            {"type": "page_number", "text": "1"},
            {"type": "dialogue", "speaker": "BOB", "text": "Dialogue 1"},
        ]

        # Act
        result, changed = processor.process(chunks)

        # Assert
        assert len(result) == 2
        assert result[0]["type"] == "action"
        assert result[1]["type"] == "dialogue"
        assert changed is True

    def test_process_multiple_skips(self):
        """Test process with multiple chunks to skip."""
        # Arrange
        processor = SkipAndMergePreProcessor({"skip_types": ["page_number", "title"]})
        chunks = [
            {"type": "action", "text": "Action 1", "raw_text": "Action 1 raw"},
            {"type": "page_number", "text": "1", "raw_text": "1 raw"},
            {"type": "title", "text": "Scene 1", "raw_text": "Scene 1 raw"},
            {"type": "action", "text": "Action 2", "raw_text": "Action 2 raw"},
        ]

        # Act
        result, changed = processor.process(chunks)

        # Assert
        assert len(result) == 1
        assert result[0]["type"] == "action"
        assert result[0]["text"] == "Action 1 Action 2"
        assert changed is True
