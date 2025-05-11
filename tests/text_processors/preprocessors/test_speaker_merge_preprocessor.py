import pytest

from script_to_speech.text_processors.preprocessors.speaker_merge_preprocessor import (
    SpeakerMergePreProcessor,
)


class TestSpeakerMergePreProcessor:
    """Tests for the SpeakerMergePreProcessor class."""

    def test_validate_config_valid(self):
        """Test validate_config with valid configuration."""
        # Arrange
        config = {
            "speakers_to_merge": {
                "BOB": ["B OB", "BO B"],
                "ALICE": ["AL ICE", "A LICE"],
            }
        }
        processor = SpeakerMergePreProcessor(config)

        # Act & Assert
        assert processor.validate_config() is True

    def test_validate_config_invalid_not_dict(self):
        """Test validate_config with invalid configuration (not a dict)."""
        # Arrange
        config = {"speakers_to_merge": "not_a_dict"}
        processor = SpeakerMergePreProcessor(config)

        # Act & Assert
        assert processor.validate_config() is False

    def test_validate_config_invalid_children_not_list(self):
        """Test validate_config with invalid configuration (children not a list)."""
        # Arrange
        config = {"speakers_to_merge": {"BOB": "not_a_list"}}
        processor = SpeakerMergePreProcessor(config)

        # Act & Assert
        assert processor.validate_config() is False

    def test_validate_config_invalid_children_not_strings(self):
        """Test validate_config with invalid configuration (children not strings)."""
        # Arrange
        config = {"speakers_to_merge": {"BOB": ["OK", 123]}}
        processor = SpeakerMergePreProcessor(config)

        # Act & Assert
        assert processor.validate_config() is False

    def test_process_empty_list(self):
        """Test process with empty chunks list."""
        # Arrange
        config = {"speakers_to_merge": {"BOB": ["B OB", "BO B"]}}
        processor = SpeakerMergePreProcessor(config)

        # Act
        result, changed = processor.process([])

        # Assert
        assert result == []
        assert changed is False

    def test_process_no_matching_chunks(self):
        """Test process with no chunks matching the mapping."""
        # Arrange
        config = {"speakers_to_merge": {"BOB": ["B OB", "BO B"]}}
        processor = SpeakerMergePreProcessor(config)
        chunks = [
            {"type": "dialog", "speaker": "ALICE", "text": "Hello there"},
            {"type": "speaker_attribution", "text": "CHARLIE"},
        ]

        # Act
        result, changed = processor.process(chunks)

        # Assert
        assert result == chunks
        assert changed is False

    def test_process_merge_speaker_attribution(self):
        """Test process merges speaker in speaker_attribution chunks."""
        # Arrange
        config = {"speakers_to_merge": {"BOB": ["B OB", "BO B"]}}
        processor = SpeakerMergePreProcessor(config)
        chunks = [
            {"type": "speaker_attribution", "text": "B OB"},
            {"type": "dialog", "speaker": "B OB", "text": "Hello there"},
        ]

        # Act
        result, changed = processor.process(chunks)

        # Assert
        assert result[0]["text"] == "BOB"
        assert result[1]["speaker"] == "BOB"
        assert changed is True

    def test_process_merge_dialog_speaker(self):
        """Test process merges speaker in dialog chunks."""
        # Arrange
        config = {"speakers_to_merge": {"BOB": ["B OB", "BO B"]}}
        processor = SpeakerMergePreProcessor(config)
        chunks = [
            {"type": "dialog", "speaker": "BO B", "text": "Hello there"},
        ]

        # Act
        result, changed = processor.process(chunks)

        # Assert
        assert result[0]["speaker"] == "BOB"
        assert changed is True

    def test_process_merge_multiple_variations(self):
        """Test process merges multiple speaker variations correctly."""
        # Arrange
        config = {
            "speakers_to_merge": {
                "BOB": ["B OB", "BO B"],
                "ALICE": ["AL ICE", "A LICE"],
            }
        }
        processor = SpeakerMergePreProcessor(config)
        chunks = [
            {"type": "speaker_attribution", "text": "B OB"},
            {"type": "dialog", "speaker": "B OB", "text": "Hello Alice"},
            {"type": "speaker_attribution", "text": "AL ICE"},
            {"type": "dialog", "speaker": "AL ICE", "text": "Hello Bob"},
            {"type": "speaker_attribution", "text": "BO B"},
            {"type": "dialog", "speaker": "BO B", "text": "Nice to meet you"},
        ]

        # Act
        result, changed = processor.process(chunks)

        # Assert
        assert result[0]["text"] == "BOB"
        assert result[1]["speaker"] == "BOB"
        assert result[2]["text"] == "ALICE"
        assert result[3]["speaker"] == "ALICE"
        assert result[4]["text"] == "BOB"
        assert result[5]["speaker"] == "BOB"
        assert changed is True

    def test_process_invalid_config(self):
        """Test process with invalid configuration."""
        # Arrange
        config = {"speakers_to_merge": "not_a_dict"}
        processor = SpeakerMergePreProcessor(config)
        chunks = [
            {"type": "dialog", "speaker": "BOB", "text": "Hello there"},
        ]

        # Act
        result, changed = processor.process(chunks)

        # Assert
        assert result == chunks
        assert changed is False

    def test_process_partial_replacement(self):
        """Test process with partial replacement in speaker_attribution."""
        # Arrange
        config = {"speakers_to_merge": {"BOB": ["B OB", "BO B"]}}
        processor = SpeakerMergePreProcessor(config)
        chunks = [
            {"type": "speaker_attribution", "text": "B OB (CONT'D)"},
        ]

        # Act
        result, changed = processor.process(chunks)

        # Assert
        assert result[0]["text"] == "BOB (CONT'D)"
        assert changed is True

    def test_process_preserves_non_matching_chunks(self):
        """Test process preserves chunks not matching any replacement rules."""
        # Arrange
        config = {"speakers_to_merge": {"BOB": ["B OB", "BO B"]}}
        processor = SpeakerMergePreProcessor(config)
        chunks = [
            {"type": "dialog", "speaker": "B OB", "text": "Hello there"},
            {"type": "action", "text": "Bob walks away"},
            {"type": "scene_heading", "text": "INT. HOUSE - DAY"},
        ]

        # Act
        result, changed = processor.process(chunks)

        # Assert
        assert result[0]["speaker"] == "BOB"
        assert result[1] == chunks[1]
        assert result[2] == chunks[2]
        assert changed is True
