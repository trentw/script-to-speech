"""
Unit tests for the state detection logic in the screenplay_parser module.

This module focuses on testing the state detection methods and probability calculations
that determine the type of each line in a screenplay.
"""

from unittest.mock import MagicMock, patch

import pytest

from script_to_speech.parser.screenplay_parser import (
    IndentationContext,
    ParserConfig,
    ScreenplayParser,
    State,
)


class TestStateDetectionMethods:
    """Tests for individual state detection methods."""

    def test_is_page_number(self):
        """Test page number detection."""
        parser = ScreenplayParser()

        # Valid page numbers (highly indented)
        assert (
            parser.is_page_number(
                "                                                                 2.                 "
            )
            is True
        )

        # Page numbers with insufficient indentation
        assert parser.is_page_number("    123.    ") is False
        assert parser.is_page_number("    45    ") is False

        # Invalid page numbers (not enough indentation)
        assert parser.is_page_number("123.") is False

        # Invalid page numbers (not numeric)
        assert parser.is_page_number("    ABC    ") is False
        assert parser.is_page_number("    123A    ") is False

    def test_is_scene_heading(self):
        """Test scene heading detection."""
        parser = ScreenplayParser()

        # Valid scene headings
        assert parser.is_scene_heading("INT. LIVING ROOM - DAY") is True
        assert parser.is_scene_heading("EXT. BEACH - SUNSET") is True
        assert parser.is_scene_heading("5 INT. OFFICE - NIGHT") is True
        assert parser.is_scene_heading("5A INT. OFFICE - NIGHT") is True
        assert parser.is_scene_heading("INT./EXT. CAR - DAY") is True

        # Invalid scene headings
        assert parser.is_scene_heading("JOHN enters the room") is False
        assert (
            parser.is_scene_heading("INTERIOR LIVING ROOM") is False
        )  # Missing period
        assert parser.is_scene_heading("int. living room") is False  # Lowercase
        assert parser.is_scene_heading("INT LIVING ROOM") is False  # Missing period

    def test_is_speaker_attribution(self):
        """Test speaker attribution detection."""
        parser = ScreenplayParser()

        # Valid speaker attributions
        assert parser.is_speaker_attribution("JOHN", 35) is True
        assert parser.is_speaker_attribution("MARY", 30) is True
        assert parser.is_speaker_attribution("JOHN (CONT'D)", 35) is True
        assert parser.is_speaker_attribution("MARY (O.S.)", 35) is True
        assert parser.is_speaker_attribution("BOB (V.O.) (CONT'D)", 35) is True
        assert parser.is_speaker_attribution("MONSIGNOR O'MALLEY", 35) is True

        # Invalid speaker attributions (indentation)
        assert (
            parser.is_speaker_attribution("JOHN", 20) is False
        )  # Too little indentation
        assert (
            parser.is_speaker_attribution("JOHN", 50) is False
        )  # Too much indentation

        # Invalid speaker attributions (not uppercase)
        assert parser.is_speaker_attribution("John", 35) is False
        assert parser.is_speaker_attribution("john", 35) is False

        # Invalid speaker attributions (contains INT./EXT.)
        assert parser.is_speaker_attribution("INT. LIVING ROOM", 35) is False
        assert parser.is_speaker_attribution("EXT. BEACH", 35) is False

    def test_is_right_aligned_action(self):
        """Test right-aligned action detection."""
        parser = ScreenplayParser()

        # Valid right-aligned actions
        assert parser.is_right_aligned_action("CUT TO:", 50) is True
        assert parser.is_right_aligned_action("FADE OUT", 50) is True
        assert parser.is_right_aligned_action("DISSOLVE TO:", 50) is True

        # Invalid right-aligned actions (indentation)
        assert (
            parser.is_right_aligned_action("CUT TO:", 30) is False
        )  # Not enough indentation

        # Invalid right-aligned actions (not uppercase)
        assert parser.is_right_aligned_action("Cut to:", 50) is False
        assert parser.is_right_aligned_action("Fade out", 50) is False

        # Invalid right-aligned actions (contains INT./EXT.)
        assert parser.is_right_aligned_action("INT. LIVING ROOM", 50) is False

    def test_is_dialogue_modifier(self):
        """Test dialogue modifier detection."""
        parser = ScreenplayParser()

        # Valid dialogue modifiers
        assert parser.is_dialogue_modifier("(angrily)") is True
        assert parser.is_dialogue_modifier("(whispering to John)") is True
        assert parser.is_dialogue_modifier("(pauses)") is True
        assert parser.is_dialogue_modifier("(beat)") is True

        # Invalid dialogue modifiers
        assert parser.is_dialogue_modifier("Not a modifier") is False
        assert parser.is_dialogue_modifier("(") is False  # Too short
        assert parser.is_dialogue_modifier(")") is False  # Too short
        assert (
            parser.is_dialogue_modifier("Hello (aside)") is False
        )  # Not starting with parenthesis

    def test_is_dual_speaker(self):
        """Test dual speaker detection."""
        parser = ScreenplayParser()

        # Valid dual speakers
        assert parser.is_dual_speaker("JOHN        MARY", 10) is True
        assert parser.is_dual_speaker("JOHN (CONT'D)        MARY (O.S.)", 10) is True
        assert (
            parser.is_dual_speaker(
                "FOLK MUSICIAN #1               FOLK MUSICIAN # 2", 10
            )
            is True
        )

        # Invalid dual speakers (not enough spacing)
        assert parser.is_dual_speaker("JOHN MARY", 10) is False
        assert parser.is_dual_speaker("JOHN  MARY", 10) is False

        # Invalid dual speakers (not all uppercase)
        assert parser.is_dual_speaker("John        MARY", 10) is False
        assert parser.is_dual_speaker("JOHN        Mary", 10) is False

        # Invalid dual speakers (too much indentation)
        assert parser.is_dual_speaker("JOHN        MARY", 35) is False


class TestStateTransitions:
    """Tests for state transitions and probability calculations."""

    @pytest.fixture
    def mock_logger(self):
        """Fixture to mock the logger."""
        with patch("script_to_speech.parser.screenplay_parser.logger") as mock:
            yield mock

    def test_title_to_scene_heading_transition(self, mock_logger):
        """Test transition from title to scene heading."""
        parser = ScreenplayParser()

        # Create a new parser with default state
        parser = ScreenplayParser()

        # Process a realistic title (centered and all caps)
        parser.process_line(
            "                                    THE TITLE                                       "
        )
        assert parser.state == State.TITLE

        # Process scene heading
        parser.process_line("INT. LIVING ROOM - DAY")
        assert parser.state == State.SCENE_HEADING
        assert parser.has_left_title is True

    def test_scene_heading_to_action_transition(self, mock_logger):
        """Test transition from scene heading to action."""
        parser = ScreenplayParser()

        # Process scene heading
        parser.process_line("INT. LIVING ROOM - DAY")
        assert parser.state == State.SCENE_HEADING

        # Process action
        parser.process_line("John enters the room.")
        assert parser.state == State.ACTION

    def test_action_to_speaker_attribution_transition(self, mock_logger):
        """Test transition from action to speaker attribution."""
        parser = ScreenplayParser()

        # Process action
        parser.process_line("John enters the room.")
        assert parser.state == State.ACTION

        # Process speaker attribution
        parser.process_line(
            "                                    JOHN                                            "
        )
        assert parser.state == State.SPEAKER_ATTRIBUTION
        assert parser.current_speaker == "JOHN"

    def test_speaker_attribution_to_dialogue_transition(self, mock_logger):
        """Test transition from speaker attribution to dialogue."""
        parser = ScreenplayParser()

        # Initialize state to ACTION to ensure we're not in TITLE state
        parser.state = State.ACTION
        parser.has_left_title = True

        # Process speaker attribution
        parser.process_line(
            "                                    JOHN                                            "
        )
        assert parser.state == State.SPEAKER_ATTRIBUTION
        assert parser.current_speaker == "JOHN"

        # Process dialogue
        parser.process_line(
            "                         Hello, how are you?                                        "
        )
        assert parser.state == State.DIALOGUE

    def test_dialogue_to_dialogue_modifier_transition(self, mock_logger):
        """Test transition from dialogue to dialogue modifier."""
        parser = ScreenplayParser()

        # Set up state
        parser.current_speaker = "JOHN"
        parser.state = State.DIALOGUE
        parser.has_left_title = True

        # Process dialogue modifier
        parser.process_line(
            "                         (pauses)                                                   "
        )
        assert parser.state == State.DIALOGUE_MODIFIER

    def test_dialogue_modifier_to_dialogue_transition(self, mock_logger):
        """Test transition from dialogue modifier to dialogue."""
        parser = ScreenplayParser()

        # Set up state
        parser.current_speaker = "JOHN"
        parser.state = State.DIALOGUE_MODIFIER
        parser.has_left_title = True

        # Process dialogue
        parser.process_line(
            "                         Hello again.                                               "
        )
        assert parser.state == State.DIALOGUE

    def test_action_to_dual_speaker_attribution_transition(self, mock_logger):
        """Test transition from action to dual speaker attribution."""
        parser = ScreenplayParser()

        # Process action
        parser.process_line("John and Mary speak simultaneously.")
        assert parser.state == State.ACTION

        # Process dual speaker attribution
        parser.process_line(
            "                     JOHN                          MARY                            "
        )
        assert parser.state == State.DUAL_SPEAKER_ATTRIBUTION
        assert parser.current_speaker == ""  # Speaker should be reset

    def test_dual_speaker_attribution_to_dual_dialogue_transition(self, mock_logger):
        """Test transition from dual speaker attribution to dual dialogue."""
        parser = ScreenplayParser()

        # Initialize state to ACTION to ensure we're not in TITLE state
        parser.state = State.ACTION
        parser.has_left_title = True

        # Process dual speaker attribution
        parser.process_line(
            "                     JOHN                          MARY                            "
        )
        assert parser.state == State.DUAL_SPEAKER_ATTRIBUTION

        # Process dual dialogue
        parser.process_line(
            "               Hello!                         Hi there!                             "
        )
        assert parser.state == State.DUAL_DIALOGUE

    def test_ambiguous_state_detection(self, mock_logger):
        """Test detection of ambiguous states."""
        parser = ScreenplayParser()

        # Test a line that could be either action or dialogue
        # Set up context to make it more likely to be dialogue
        parser.current_speaker = "JOHN"
        parser.state = State.DIALOGUE
        parser.has_left_title = True

        # Process ambiguous line with dialogue indentation
        parser.process_line(
            "                         This could be dialogue or action.                            "
        )
        assert parser.state == State.DIALOGUE

        # Reset and set up context to make it more likely to be action
        parser.reset_parser_state()
        parser.state = State.ACTION
        parser.has_left_title = True

        # Process ambiguous line with action indentation
        parser.process_line("This could be dialogue or action.")
        assert parser.state == State.ACTION


class TestEdgeCases:
    """Tests for edge cases in state detection."""

    @pytest.fixture
    def mock_logger(self):
        """Fixture to mock the logger."""
        with patch("script_to_speech.parser.screenplay_parser.logger") as mock:
            yield mock

    def test_empty_line_handling(self, mock_logger):
        """Test handling of empty lines."""
        parser = ScreenplayParser()

        # Set initial state
        parser.state = State.ACTION

        # Process empty line
        state = parser.determine_state("", 0)

        # Empty line should return None
        assert state is None

        # State should not change
        assert parser.state == State.ACTION

    def test_whitespace_only_line_handling(self, mock_logger):
        """Test handling of whitespace-only lines."""
        parser = ScreenplayParser()

        # Set initial state
        parser.state = State.ACTION

        # Process whitespace-only line
        state = parser.determine_state("    ", 4)

        # Whitespace-only line should return None
        assert state is None

        # State should not change
        assert parser.state == State.ACTION

    def test_unusual_formatting(self, mock_logger):
        """Test handling of unusually formatted lines."""
        parser = ScreenplayParser()

        # Test mixed case scene heading
        state = parser.determine_state("Int. Living Room - Day", 0)

        # Should not be detected as scene heading due to mixed case
        assert state != State.SCENE_HEADING

        # Test mixed case speaker attribution
        state = parser.determine_state(
            "                                    John                                            ",
            36,
        )

        # Should not be detected as speaker attribution due to mixed case
        assert state != State.SPEAKER_ATTRIBUTION
