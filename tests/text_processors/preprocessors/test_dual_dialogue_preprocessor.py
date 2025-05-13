import pytest

from script_to_speech.text_processors.preprocessors.dual_dialogue_preprocessor import (
    DualDialoguePreProcessor,
)


class TestDualDialoguePreProcessor:
    """Tests for the DualDialoguePreProcessor class."""

    def test_validate_config_empty(self):
        """Test validation with empty configuration."""
        # Arrange
        config = {}
        processor = DualDialoguePreProcessor(config)

        # Act & Assert
        assert processor.validate_config() is True
        # Verify defaults were applied
        assert (
            processor.min_speaker_spacing
            == DualDialoguePreProcessor.DEFAULT_MIN_SPEAKER_SPACING
        )
        assert (
            processor.min_dialogue_spacing
            == DualDialoguePreProcessor.DEFAULT_MIN_DIALOGUE_SPACING
        )

    def test_validate_config_valid(self):
        """Test validation with valid configuration."""
        # Arrange
        config = {"min_speaker_spacing": 8, "min_dialogue_spacing": 4}
        processor = DualDialoguePreProcessor(config)

        # Act & Assert
        assert processor.validate_config() is True
        # Verify config values were applied
        assert processor.min_speaker_spacing == 8
        assert processor.min_dialogue_spacing == 4

    def test_validate_config_invalid_type(self):
        """Test validation with invalid type for spacing values."""
        # Arrange - Test with strings instead of integers
        config = {"min_speaker_spacing": "8", "min_dialogue_spacing": 4}
        processor = DualDialoguePreProcessor(config)

        # Act & Assert
        assert processor.validate_config() is False

        # Arrange - Test with string for dialogue spacing
        config = {"min_speaker_spacing": 8, "min_dialogue_spacing": "4"}
        processor = DualDialoguePreProcessor(config)

        # Act & Assert
        assert processor.validate_config() is False

    def test_validate_config_invalid_value(self):
        """Test validation with invalid values for spacing parameters."""
        # Arrange - Test with zero speaker spacing
        config = {"min_speaker_spacing": 0, "min_dialogue_spacing": 4}
        processor = DualDialoguePreProcessor(config)

        # Act & Assert
        assert processor.validate_config() is False

        # Arrange - Test with negative dialogue spacing
        config = {"min_speaker_spacing": 8, "min_dialogue_spacing": -1}
        processor = DualDialoguePreProcessor(config)

        # Act & Assert
        assert processor.validate_config() is False

    def test_process_empty_list(self):
        """Test processing of empty chunk list."""
        # Arrange
        processor = DualDialoguePreProcessor({})

        # Act
        result, changed = processor.process([])

        # Assert
        assert result == []
        assert changed is False

    def test_split_speakers_full(self):
        """Test splitting a dual speaker attribution into two speakers."""
        # Arrange
        processor = DualDialoguePreProcessor({})
        speaker_text = "SPEAKER1                     SPEAKER2"

        # Act
        left, right = processor._split_speakers_full(speaker_text)

        # Assert
        assert left == "SPEAKER1"
        assert right == "SPEAKER2"

    def test_split_speakers_full_custom_spacing(self):
        """Test splitting speakers with custom spacing configuration."""
        # Arrange - Configure with higher min_speaker_spacing
        processor = DualDialoguePreProcessor({"min_speaker_spacing": 10})

        # This should split correctly with 10+ spaces
        speaker_text = "SPEAKER1           SPEAKER2"

        # Act
        left, right = processor._split_speakers_full(speaker_text)

        # Assert
        assert left == "SPEAKER1"
        assert right == "SPEAKER2"

        # Arrange - Test another speaker with parentheticals that should split
        speaker_text = "SPEAKER1 (CONT'D)            SPEAKER2 (V.O.)"

        # Act
        left, right = processor._split_speakers_full(speaker_text)

        # Assert
        assert left == "SPEAKER1 (CONT'D)"
        assert right == "SPEAKER2 (V.O.)"

    def test_split_speakers_full_error(self):
        """Test error handling when splitting speakers fails."""
        # Arrange
        processor = DualDialoguePreProcessor({})
        # Not enough spacing between text to split into two parts
        speaker_text = "SPEAKER1 SPEAKER2"

        # Act & Assert
        with pytest.raises(ValueError) as excinfo:
            processor._split_speakers_full(speaker_text)
        assert "Could not split speakers" in str(excinfo.value)

    def test_process_basic_dual_dialogue(self):
        """Test basic processing of a dual dialogue chunk pair."""
        # Arrange
        processor = DualDialoguePreProcessor({})
        chunks = [
            {
                "type": "dual_speaker_attribution",
                "speaker": "",
                "raw_text": "                     FOLK MUSICIAN #1               FOLK MUSICIAN # 2               ",
                "text": "FOLK MUSICIAN #1               FOLK MUSICIAN # 2",
            },
            {
                "type": "dual_dialogue",
                "speaker": "",
                "raw_text": "               Yes!                           Woody ain't singing anymore,          \n                                              is he?                                ",
                "text": "Yes!                           Woody ain't singing anymore, is he?",
            },
        ]

        # Act
        result, changed = processor.process(chunks)

        # Assert
        assert changed is True
        assert len(result) == 4
        # First chunk should be speaker attribution for left speaker
        assert result[0]["type"] == "speaker_attribution"
        assert result[0]["text"] == "FOLK MUSICIAN #1"
        assert result[0]["speaker"] == ""
        # Second chunk should be dialogue for left speaker
        assert result[1]["type"] == "dialogue"
        assert result[1]["text"] == "Yes!"
        assert result[1]["speaker"] == "FOLK MUSICIAN #1"
        # Third chunk should be speaker attribution for right speaker
        assert result[2]["type"] == "speaker_attribution"
        assert result[2]["text"] == "FOLK MUSICIAN # 2"
        assert result[2]["speaker"] == ""
        # Fourth chunk should be dialogue for right speaker
        assert result[3]["type"] == "dialogue"
        assert result[3]["text"] == "Woody ain't singing anymore, is he?"
        assert result[3]["speaker"] == "FOLK MUSICIAN # 2"

    def test_process_dual_dialogue_with_midcolumn_speaker_change(self):
        """Test processing of dual dialogue with new speaker introduced in the middle of a column."""
        # Arrange
        processor = DualDialoguePreProcessor({})
        chunks = [
            {
                "type": "dual_speaker_attribution",
                "speaker": "",
                "raw_text": "                           MCKAY                        VTR TECH                  ",
                "text": "MCKAY                        VTR TECH",
            },
            {
                "type": "dual_dialogue",
                "speaker": "",
                "raw_text": "                 (over speakers)                (quietly into headset)            \n               After receiving a law degree   Rolling, ready in seven,            \n               from Columbia University,      six,                                \n               Berger failed to qualify for   five,                               \n               the US team. To fulfill his    four,                               \n               dream of the Olympics, he      three,                              \n               emigrated to Israel. Two days  two,                                \n               ago, he was interviewed by     one. 5 ready to go.                 \n               Peter Jennings for an ABC                  GEOFF                   \n               color piece.                        (over headset)                 \n                                              Hit it.                             ",
                "text": "(over speakers)                (quietly into headset) After receiving a law degree   Rolling, ready in seven, from Columbia University,      six, Berger failed to qualify for   five, the US team. To fulfill his    four, dream of the Olympics, he      three, emigrated to Israel. Two days  two, ago, he was interviewed by     one. 5 ready to go. Peter Jennings for an ABC                  GEOFF color piece.                        (over headset) Hit it.",
            },
        ]

        # Act
        result, changed = processor.process(chunks)

        # Assert
        assert changed is True

        # Examining the complex output
        # Left column: MCKAY -> parenthetical -> dialogue
        assert result[0]["type"] == "speaker_attribution"
        assert result[0]["text"] == "MCKAY"
        assert result[1]["type"] == "dialogue_modifier"
        assert result[1]["text"] == "(over speakers)"
        assert result[2]["type"] == "dialogue"
        assert (
            result[2]["text"]
            == "After receiving a law degree from Columbia University, Berger failed to qualify for the US team. To fulfill his dream of the Olympics, he emigrated to Israel. Two days ago, he was interviewed by Peter Jennings for an ABC color piece."
        )
        assert result[2]["speaker"] == "MCKAY"

        # Right column: VTR TECH -> parenthetical -> dialogue -> GEOFF -> parenthetical -> dialogue
        assert result[3]["type"] == "speaker_attribution"
        assert result[3]["text"] == "VTR TECH"
        assert result[4]["type"] == "dialogue_modifier"
        assert result[4]["text"] == "(quietly into headset)"
        assert result[5]["type"] == "dialogue"
        assert (
            result[5]["text"]
            == "Rolling, ready in seven, six, five, four, three, two, one. 5 ready to go."
        )
        assert result[5]["speaker"] == "VTR TECH"
        assert result[6]["type"] == "speaker_attribution"
        assert result[6]["text"] == "GEOFF"
        assert result[7]["type"] == "dialogue_modifier"
        assert result[7]["text"] == "(over headset)"
        assert result[8]["type"] == "dialogue"
        assert result[8]["text"] == "Hit it."
        assert result[8]["speaker"] == "GEOFF"

    def test_process_dual_dialogue_with_language_markers(self):
        """Test processing of dual dialogue with language markers in parentheticals."""
        # Arrange
        processor = DualDialoguePreProcessor(
            {"min_speaker_spacing": 2, "min_dialogue_spacing": 2}
        )
        chunks = [
            {
                "type": "dual_speaker_attribution",
                "speaker": "",
                "raw_text": "                    HIAS REPRESENTATIVE (CONT'D)  HIAS REPRESENTATIVE 2 (CONT'D)    ",
                "text": "HIAS REPRESENTATIVE (CONT'D)  HIAS REPRESENTATIVE 2 (CONT'D)",
            },
            {
                "type": "dual_dialogue",
                "speaker": "",
                "raw_text": "                 (English)                      (Yiddish)                           \n               And for those of you of which  And for those of you of which         \n               none of the aforementioned     none of that applies and who          \n               details apply and who are      are immediately departing for         \n               immediately departing for      other destinations in the             \n               other destinations in the      morning, please see us about          \n               morning, please see me about   a $25 travel-aid.                     \n               your $25 travel-aid.                                                 ",
                "text": "(English)                      (Yiddish) And for those of you of which  And for those of you of which none of the aforementioned     none of that applies and who details apply and who are      are immediately departing for immediately departing for      other destinations in the other destinations in the      morning, please see us about morning, please see me about   a $25 travel-aid. your $25 travel-aid.",
            },
        ]

        # Act
        result, changed = processor.process(chunks)

        # Assert
        assert changed is True

        # Should have 2 speakers, 2 parentheticals, 2 dialogue chunks
        assert len(result) == 6

        # Left column
        assert result[0]["type"] == "speaker_attribution"
        assert result[0]["text"] == "HIAS REPRESENTATIVE (CONT'D)"
        assert result[0]["speaker"] == ""
        assert result[1]["type"] == "dialogue_modifier"
        assert result[1]["text"] == "(English)"
        assert result[1]["speaker"] == ""
        assert result[2]["type"] == "dialogue"
        assert (
            result[2]["text"]
            == "And for those of you of which none of the aforementioned details apply and who are immediately departing for other destinations in the morning, please see me about your $25 travel-aid."
        )
        assert result[2]["speaker"] == "HIAS REPRESENTATIVE"

        # Right column
        assert result[3]["type"] == "speaker_attribution"
        assert result[3]["text"] == "HIAS REPRESENTATIVE 2 (CONT'D)"
        assert result[3]["speaker"] == ""
        assert result[4]["type"] == "dialogue_modifier"
        assert result[4]["text"] == "(Yiddish)"
        assert result[4]["speaker"] == ""
        assert result[5]["type"] == "dialogue"
        assert (
            result[5]["text"]
            == "And for those of you of which none of that applies and who are immediately departing for other destinations in the morning, please see us about a $25 travel-aid."
        )
        assert result[5]["speaker"] == "HIAS REPRESENTATIVE 2"

    def test_process_noncontiguous_dual_dialogue(self):
        """Test that dual dialogue processing only happens for contiguous dual_speaker_attribution and dual_dialogue."""
        # Arrange
        processor = DualDialoguePreProcessor({})
        chunks = [
            {
                "type": "dual_speaker_attribution",
                "speaker": "",
                "text": "SPEAKER1                       SPEAKER2",
            },
            {
                "type": "action",  # Should prevent dual dialogue processing
                "text": "Some action happens",
            },
            {
                "type": "dual_dialogue",
                "speaker": "",
                "text": "Line 1                         Line 2",
            },
        ]

        # Act
        result, changed = processor.process(chunks)

        # Assert
        assert changed is False
        assert result == chunks  # Should remain unchanged

    def test_process_dialogue_splitting_with_custom_spacing(self):
        """Test that dialogue splitting uses the configured min_dialogue_spacing correctly."""
        # Arrange
        processor = DualDialoguePreProcessor({"min_dialogue_spacing": 2})
        chunks = [
            {
                "type": "dual_speaker_attribution",
                "speaker": "",
                "raw_text": "                     NEWS REPORTER                     MARIANNE (CONT'D)         ",
                "text": "NEWS REPORTER                     MARIANNE (CONT'D)",
            },
            {
                "type": "dual_dialogue",
                "speaker": "",
                "raw_text": "               .... erreichen uns immer mehr  There have been reports of          \n               Meldungen, dass es einen       shots being fired inside the        \n               Schusswechsel innerhalb des    Olympic Village.                    \n               Olympischen Dorfes gab.                                            ",
                "text": ".... erreichen uns immer mehr  There have been reports of Meldungen, dass es einen       shots being fired inside the Schusswechsel innerhalb des    Olympic Village. Olympischen Dorfes gab.",
            },
        ]

        # Act
        result, changed = processor.process(chunks)

        # Assert
        assert changed is True
        # Verify the number of chunks and correctness of splitting
        assert len(result) == 4
        assert result[0]["type"] == "speaker_attribution"
        assert result[0]["text"] == "NEWS REPORTER"
        assert result[1]["type"] == "dialogue"
        assert (
            result[1]["text"]
            == ".... erreichen uns immer mehr Meldungen, dass es einen Schusswechsel innerhalb des Olympischen Dorfes gab."
        )
        assert result[1]["speaker"] == "NEWS REPORTER"
        assert result[2]["type"] == "speaker_attribution"
        assert result[2]["text"] == "MARIANNE (CONT'D)"
        assert result[3]["type"] == "dialogue"
        assert (
            result[3]["text"]
            == "There have been reports of shots being fired inside the Olympic Village."
        )
        assert result[3]["speaker"] == "MARIANNE"

    def test_process_dual_dialogue_with_non_dual_chunks(self):
        """Test processing when chunks include both dual and non-dual dialogue elements."""
        # Arrange
        processor = DualDialoguePreProcessor({})
        chunks = [
            {"type": "action", "text": "The scene begins."},
            {
                "type": "dual_speaker_attribution",
                "speaker": "",
                "raw_text": "                     FOLK MUSICIAN #1               FOLK MUSICIAN # 2               ",
                "text": "FOLK MUSICIAN #1               FOLK MUSICIAN # 2",
            },
            {
                "type": "dual_dialogue",
                "speaker": "",
                "raw_text": "               Yes!                           Woody ain't singing anymore,          \n                                              is he?                                ",
                "text": "Yes!                           Woody ain't singing anymore, is he?",
            },
            {"type": "action", "text": "They look at each other."},
            {"type": "speaker_attribution", "speaker": "", "text": "FOLK MUSICIAN #1"},
            {
                "type": "dialogue",
                "speaker": "FOLK MUSICIAN #1",
                "text": "That's what I thought.",
            },
        ]

        # Act
        result, changed = processor.process(chunks)

        # Assert
        assert changed is True
        # First and last three chunks should remain unchanged
        assert result[0] == chunks[0]
        assert result[5] == chunks[3]
        assert result[6] == chunks[4]
        assert result[7] == chunks[5]
        # Middle should be transformed
        assert (
            len(result) == 8
        )  # Original 6 plus 2 new ones (from dual dialogue split into 4)
        assert result[1]["type"] == "speaker_attribution"
        assert result[1]["text"] == "FOLK MUSICIAN #1"
        assert result[2]["type"] == "dialogue"
        assert result[2]["text"] == "Yes!"
        assert result[3]["type"] == "speaker_attribution"
        assert result[3]["text"] == "FOLK MUSICIAN # 2"
        assert result[4]["type"] == "dialogue"
        assert result[4]["text"] == "Woody ain't singing anymore, is he?"

    def test_clean_speaker_name(self):
        """Test that parentheticals are removed from speaker names."""
        # Arrange
        processor = DualDialoguePreProcessor({})

        # Act & Assert - Basic parenthetical
        assert processor._clean_speaker_name("SPEAKER (CONT'D)") == "SPEAKER"

        # Act & Assert - Multiple parentheticals
        assert processor._clean_speaker_name("SPEAKER (CONT'D) (O.S.)") == "SPEAKER"

        # Act & Assert - No parentheticals
        assert processor._clean_speaker_name("SPEAKER") == "SPEAKER"

        # Act & Assert - With whitespace
        assert processor._clean_speaker_name("  SPEAKER (CONT'D)  ") == "SPEAKER"

    def test_split_dialogue_indentation_handling(self):
        """Test that dialogue splitting properly handles indentation between columns."""
        # Arrange
        processor = DualDialoguePreProcessor({})
        raw_dialogue = """               First line left               First line right
               Second line left              Second line right
                    Indented line left           Indented line right
               Third line left               Third line right
             Unindented line left          Unindented line right"""

        # Act
        left_lines, right_lines = processor._split_dialogue(raw_dialogue)

        # Assert
        assert len(left_lines) == 5
        assert len(right_lines) == 5
        assert left_lines[0] == "First line left"
        assert right_lines[0] == "First line right"
        assert left_lines[1] == "Second line left"
        assert right_lines[1] == "Second line right"
        assert left_lines[2] == "Indented line left"
        assert right_lines[2] == "Indented line right"
        assert left_lines[3] == "Third line left"
        assert right_lines[3] == "Third line right"
        assert left_lines[4] == "Unindented line left"
        assert right_lines[4] == "Unindented line right"

    def test_process_multi_config_mode(self):
        """Test that the multi_config_mode property returns 'override'."""
        # Arrange
        processor = DualDialoguePreProcessor({})

        # Act & Assert
        assert processor.multi_config_mode == "override"

    def test_complex_multilevel_dialogue(self):
        """Test processing of complex multilevel dual dialogue with nested speakers."""
        # Arrange
        processor = DualDialoguePreProcessor({})
        chunks = [
            {
                "type": "dual_speaker_attribution",
                "speaker": "",
                "raw_text": "                           MCKAY                        VTR TECH                  ",
                "text": "MCKAY                        VTR TECH",
            },
            {
                "type": "dual_dialogue",
                "speaker": "",
                "raw_text": "                 (over speakers)                (quietly into headset)            \n               After receiving a law degree   Rolling, ready in seven,            \n               from Columbia University,      six,                                \n               Berger failed to qualify for   five,                               \n               the US team. To fulfill his    four,                               \n               dream of the Olympics, he      three,                              \n               emigrated to Israel. Two days  two,                                \n               ago, he was interviewed by     one. 5 ready to go.                 \n               Peter Jennings for an ABC                  GEOFF                   \n               color piece.                        (over headset)                 \n                                              Hit it.                             ",
                "text": "(over speakers)                (quietly into headset) After receiving a law degree   Rolling, ready in seven, from Columbia University,      six, Berger failed to qualify for   five, the US team. To fulfill his    four, dream of the Olympics, he      three, emigrated to Israel. Two days  two, ago, he was interviewed by     one. 5 ready to go. Peter Jennings for an ABC                  GEOFF color piece.                        (over headset) Hit it.",
            },
        ]

        # Process once and verify results (already tested in test_process_dual_dialogue_with_midcolumn_speaker_change)
        result, _ = processor.process(chunks)

        # Now feed the result back through the processor to verify it doesn't change
        new_result, changed = processor.process(result)

        # The processor should not make any changes to already processed content
        assert changed is False
        assert len(new_result) == len(result)

    def test_invalid_split_handling(self):
        """Test handling of edge cases where splitting might fail."""
        # Arrange
        processor = DualDialoguePreProcessor({})
        # Create a dual dialogue pair with problematic format - speaker line that looks like it should split
        # but dialogue doesn't have clear columns
        chunks = [
            {
                "type": "dual_speaker_attribution",
                "speaker": "",
                "raw_text": "                     SPEAKER ONE                    SPEAKER TWO                  ",
                "text": "SPEAKER ONE                    SPEAKER TWO",
            },
            {
                "type": "dual_dialogue",
                "speaker": "",
                # Dialogue without clear column separation
                "raw_text": "               This dialogue doesn't have proper spacing to split into columns      \n               because it's all on the left side without proper format             ",
                "text": "This dialogue doesn't have proper spacing to split into columns because it's all on the left side without proper format",
            },
        ]

        # Act - The processor should still try to process this
        result, changed = processor.process(chunks)

        # Assert
        assert changed is True
        # Check what happened - likely one speaker got all the text and the other got nothing
        assert len(result) >= 2
        assert result[0]["type"] == "speaker_attribution"
        assert result[0]["text"] == "SPEAKER ONE"

        # The first speaker should have all the dialogue text
        found_speaker_one_dialogue = False
        for chunk in result:
            if chunk["type"] == "dialogue" and chunk["speaker"] == "SPEAKER ONE":
                found_speaker_one_dialogue = True
                assert "dialogue doesn't have proper spacing" in chunk["text"]
                break

        assert (
            found_speaker_one_dialogue
        ), "Speaker one should have received the dialogue text"
