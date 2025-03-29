"""
Unit tests for the chunk processing logic in the screenplay_parser module.

This module focuses on testing the chunk creation, modification, and completion
functionality in the screenplay parser.
"""

from parser.screenplay_parser import (
    Chunk,
    IndentationContext,
    ParserConfig,
    ScreenplayParser,
    State,
)
from unittest.mock import MagicMock, patch

import pytest


class TestChunkCreation:
    """Tests for chunk creation."""

    @pytest.fixture
    def mock_logger(self):
        """Fixture to mock the logger."""
        with patch("parser.screenplay_parser.logger") as mock:
            yield mock

    def test_create_title_chunk(self, mock_logger):
        """Test creation of a title chunk."""
        parser = ScreenplayParser()

        # Handle transition to title
        parser.handle_state_transition("TITLE", State.TITLE)

        # Check chunk was created correctly
        assert parser.current_chunk is not None
        assert parser.current_chunk.type == "title"
        assert parser.current_chunk.speaker is None
        assert parser.current_chunk.raw_text == "TITLE"
        assert parser.current_chunk.text == "TITLE"

    def test_create_scene_heading_chunk(self, mock_logger):
        """Test creation of a scene heading chunk."""
        parser = ScreenplayParser()

        # Handle transition to scene heading
        parser.handle_state_transition("INT. LIVING ROOM - DAY", State.SCENE_HEADING)

        # Check chunk was created correctly
        assert parser.current_chunk is not None
        assert parser.current_chunk.type == "scene_heading"
        assert parser.current_chunk.speaker is None
        assert parser.current_chunk.raw_text == "INT. LIVING ROOM - DAY"
        assert parser.current_chunk.text == "INT. LIVING ROOM - DAY"

    def test_create_action_chunk(self, mock_logger):
        """Test creation of an action chunk."""
        parser = ScreenplayParser()

        # Handle transition to action
        parser.handle_state_transition("John enters the room.", State.ACTION)

        # Check chunk was created correctly
        assert parser.current_chunk is not None
        assert parser.current_chunk.type == "action"
        assert parser.current_chunk.speaker is None
        assert parser.current_chunk.raw_text == "John enters the room."
        assert parser.current_chunk.text == "John enters the room."

    def test_create_speaker_attribution_chunk(self, mock_logger):
        """Test creation of a speaker attribution chunk."""
        parser = ScreenplayParser()

        # Handle transition to speaker attribution
        parser.handle_state_transition(
            "                                    JOHN                                            ",
            State.SPEAKER_ATTRIBUTION,
        )

        # Check chunk was created correctly
        assert parser.current_chunk is not None
        assert parser.current_chunk.type == "speaker_attribution"
        assert parser.current_chunk.speaker is None
        assert (
            parser.current_chunk.raw_text
            == "                                    JOHN                                            "
        )
        assert parser.current_chunk.text == "JOHN"

        # Check speaker was tracked
        assert parser.current_speaker == "JOHN"

    def test_create_dialog_chunk(self, mock_logger):
        """Test creation of a dialog chunk."""
        parser = ScreenplayParser()

        # Set up speaker
        parser.current_speaker = "JOHN"

        # Handle transition to dialog
        parser.handle_state_transition(
            "                         Hello, how are you?                                        ",
            State.DIALOG,
        )

        # Check chunk was created correctly
        assert parser.current_chunk is not None
        assert parser.current_chunk.type == "dialog"
        assert parser.current_chunk.speaker == "JOHN"
        assert (
            parser.current_chunk.raw_text
            == "                         Hello, how are you?                                        "
        )
        assert parser.current_chunk.text == "Hello, how are you?"

    def test_create_dialog_modifier_chunk(self, mock_logger):
        """Test creation of a dialog modifier chunk."""
        parser = ScreenplayParser()

        # Handle transition to dialog modifier
        parser.handle_state_transition(
            "                         (pauses)                                                   ",
            State.DIALOG_MODIFIER,
        )

        # Check chunk was created correctly
        assert parser.current_chunk is not None
        assert parser.current_chunk.type == "dialog_modifier"
        assert parser.current_chunk.speaker is None
        assert (
            parser.current_chunk.raw_text
            == "                         (pauses)                                                   "
        )
        assert parser.current_chunk.text == "(pauses)"

    def test_create_dual_speaker_attribution_chunk(self, mock_logger):
        """Test creation of a dual speaker attribution chunk."""
        parser = ScreenplayParser()

        # Handle transition to dual speaker attribution
        parser.handle_state_transition(
            "                     JOHN                          MARY                            ",
            State.DUAL_SPEAKER_ATTRIBUTION,
        )

        # Check chunk was created correctly
        assert parser.current_chunk is not None
        assert parser.current_chunk.type == "dual_speaker_attribution"
        assert parser.current_chunk.speaker is None
        assert (
            parser.current_chunk.raw_text
            == "                     JOHN                          MARY                            "
        )
        assert parser.current_chunk.text == "JOHN                          MARY"

        # Check speaker was reset
        assert parser.current_speaker == ""

    def test_create_dual_dialog_chunk(self, mock_logger):
        """Test creation of a dual dialog chunk."""
        parser = ScreenplayParser()

        # Handle transition to dual dialog
        parser.handle_state_transition(
            "               Hello!                         Hi there!                             ",
            State.DUAL_DIALOG,
        )

        # Check chunk was created correctly
        assert parser.current_chunk is not None
        assert parser.current_chunk.type == "dual_dialog"
        assert parser.current_chunk.speaker is None
        assert (
            parser.current_chunk.raw_text
            == "               Hello!                         Hi there!                             "
        )
        assert parser.current_chunk.text == "Hello!                         Hi there!"

    def test_create_page_number_chunk(self, mock_logger):
        """Test creation of a page number chunk."""
        parser = ScreenplayParser()

        # Handle transition to page number
        parser.handle_state_transition(
            "                                                                 2.                 ",
            State.PAGE_NUMBER,
        )

        # Check chunk was created correctly
        assert parser.current_chunk is not None
        assert parser.current_chunk.type == "page_number"
        assert parser.current_chunk.speaker is None
        assert (
            parser.current_chunk.raw_text
            == "                                                                 2.                 "
        )
        assert parser.current_chunk.text == "2."


class TestChunkContinuation:
    """Tests for chunk continuation."""

    @pytest.fixture
    def mock_logger(self):
        """Fixture to mock the logger."""
        with patch("parser.screenplay_parser.logger") as mock:
            yield mock

    def test_continue_action_chunk(self, mock_logger):
        """Test continuation of an action chunk."""
        parser = ScreenplayParser()

        # Create initial action chunk
        parser.handle_state_transition("John enters the room.", State.ACTION)
        initial_chunk = parser.current_chunk

        # Continue with same state
        parser.handle_state_transition("He looks around.", State.ACTION)

        # Check chunk was continued
        assert parser.current_chunk is initial_chunk
        assert (
            parser.current_chunk.raw_text == "John enters the room.\nHe looks around."
        )
        assert parser.current_chunk.text == "John enters the room. He looks around."

    def test_continue_dialog_chunk(self, mock_logger):
        """Test continuation of a dialog chunk."""
        parser = ScreenplayParser()

        # Set up speaker
        parser.current_speaker = "JOHN"

        # Create initial dialog chunk
        parser.handle_state_transition(
            "                         Hello, how are you?                                        ",
            State.DIALOG,
        )
        initial_chunk = parser.current_chunk

        # Continue with same state
        parser.handle_state_transition(
            "                         I've been looking for you.                                 ",
            State.DIALOG,
        )

        # Check chunk was continued
        assert parser.current_chunk is initial_chunk
        assert (
            parser.current_chunk.raw_text
            == "                         Hello, how are you?                                        \n                         I've been looking for you.                                 "
        )
        assert (
            parser.current_chunk.text
            == "Hello, how are you? I've been looking for you."
        )

    def test_continue_scene_heading_chunk(self, mock_logger):
        """Test continuation of a scene heading chunk."""
        parser = ScreenplayParser()

        # Create initial scene heading chunk
        parser.handle_state_transition("INT. LIVING ROOM - DAY", State.SCENE_HEADING)
        initial_chunk = parser.current_chunk

        # Continue with same state
        parser.handle_state_transition("CONTINUED:", State.SCENE_HEADING)

        # Check chunk was continued
        assert parser.current_chunk is initial_chunk
        assert parser.current_chunk.raw_text == "INT. LIVING ROOM - DAY\nCONTINUED:"
        assert parser.current_chunk.text == "INT. LIVING ROOM - DAY CONTINUED:"

    def test_continue_dual_dialog_chunk(self, mock_logger):
        """Test continuation of a dual dialog chunk."""
        parser = ScreenplayParser()

        # Create initial dual dialog chunk
        parser.handle_state_transition(
            "               Hello!                         Hi there!                             ",
            State.DUAL_DIALOG,
        )
        initial_chunk = parser.current_chunk

        # Continue with same state
        parser.handle_state_transition(
            "               How are you?                   I'm good!                             ",
            State.DUAL_DIALOG,
        )

        # Check chunk was continued
        assert parser.current_chunk is initial_chunk
        assert (
            parser.current_chunk.raw_text
            == "               Hello!                         Hi there!                             \n               How are you?                   I'm good!                             "
        )
        assert (
            parser.current_chunk.text
            == "Hello!                         Hi there! How are you?                   I'm good!"
        )


class TestChunkCompletion:
    """Tests for chunk completion."""

    @pytest.fixture
    def mock_logger(self):
        """Fixture to mock the logger."""
        with patch("parser.screenplay_parser.logger") as mock:
            yield mock

    def test_complete_chunk_on_state_change(self, mock_logger):
        """Test chunk completion when state changes."""
        parser = ScreenplayParser()

        # Create scene heading chunk
        parser.handle_state_transition("INT. LIVING ROOM - DAY", State.SCENE_HEADING)

        # Change state to action
        parser.handle_state_transition("John enters the room.", State.ACTION)

        # Check scene heading was added to chunks
        assert len(parser.chunks) == 1
        assert parser.chunks[0].type == "scene_heading"

        # Check new action chunk is current
        assert parser.current_chunk.type == "action"

    def test_process_line_returns_completed_chunks(self, mock_logger):
        """Test that process_line returns completed chunks."""
        parser = ScreenplayParser()

        # Process scene heading
        completed_chunks = parser.process_line("INT. LIVING ROOM - DAY")

        # No completed chunks yet
        assert completed_chunks == []

        # Process action (completes scene heading)
        completed_chunks = parser.process_line("John enters the room.")

        # Scene heading should be completed
        assert len(completed_chunks) == 1
        assert completed_chunks[0]["type"] == "scene_heading"

        # Process speaker attribution (completes action)
        completed_chunks = parser.process_line(
            "                                    JOHN                                            "
        )

        # Action should be completed
        assert len(completed_chunks) == 1
        assert completed_chunks[0]["type"] == "action"

    def test_get_completed_chunks(self, mock_logger):
        """Test getting completed chunks at the end of parsing."""
        parser = ScreenplayParser()

        # Process some lines
        parser.process_line("INT. LIVING ROOM - DAY")
        parser.process_line("John enters the room.")
        parser.process_line(
            "                                    JOHN                                            "
        )
        parser.process_line(
            "                         Hello, how are you?                                        "
        )

        # Get completed chunks - this only returns the current chunk (dialog)
        completed_chunks = parser.get_completed_chunks()

        # Only the current chunk (dialog) should be returned
        assert len(completed_chunks) == 1

        # Check the dialog chunk
        dialog_chunk = completed_chunks[0]
        assert dialog_chunk["type"] == "dialog"
        assert dialog_chunk["speaker"] == "JOHN"
        assert dialog_chunk["text"] == "Hello, how are you?"

        # Current chunk should be reset
        assert parser.current_chunk is None

    def test_chunk_to_dict_conversion(self, mock_logger):
        """Test conversion of Chunk objects to dictionaries."""
        parser = ScreenplayParser()

        # Create a chunk and set it as the current chunk
        chunk = Chunk(
            type="dialog",
            speaker="JOHN",
            raw_text="                         Hello, how are you?                                        ",
            text="Hello, how are you?",
        )

        # Set as current chunk instead of adding to parser.chunks
        parser.current_chunk = chunk

        # Get completed chunks - this converts the current chunk to a dict
        completed_chunks = parser.get_completed_chunks()

        # Check conversion to dict
        assert len(completed_chunks) == 1
        assert isinstance(completed_chunks[0], dict)
        assert completed_chunks[0]["type"] == "dialog"
        assert completed_chunks[0]["speaker"] == "JOHN"
        assert (
            completed_chunks[0]["raw_text"]
            == "                         Hello, how are you?                                        "
        )
        assert completed_chunks[0]["text"] == "Hello, how are you?"


class TestSpeakerTracking:
    """Tests for speaker tracking during chunk processing."""

    @pytest.fixture
    def mock_logger(self):
        """Fixture to mock the logger."""
        with patch("parser.screenplay_parser.logger") as mock:
            yield mock

    def test_speaker_tracking_basic(self, mock_logger):
        """Test basic speaker tracking."""
        parser = ScreenplayParser()

        # Initialize state to ACTION to ensure we're not in TITLE state
        parser.state = State.ACTION
        parser.has_left_title = True

        # Process speaker attribution
        parser.process_line(
            "                                    JOHN                                            "
        )

        # Check speaker was tracked
        assert parser.current_speaker == "JOHN"

        # Process dialog
        parser.process_line(
            "                         Hello, how are you?                                        "
        )

        # Check speaker was applied to dialog
        assert parser.current_chunk.speaker == "JOHN"

    def test_speaker_tracking_with_parentheticals(self, mock_logger):
        """Test speaker tracking with parentheticals."""
        parser = ScreenplayParser()

        # Initialize state to ACTION to ensure we're not in TITLE state
        parser.state = State.ACTION
        parser.has_left_title = True

        # Process speaker attribution with parenthetical
        parser.process_line(
            "                                    JOHN (CONT'D)                                   "
        )

        # Check speaker was tracked without parenthetical
        assert parser.current_speaker == "JOHN"

        # Process dialog
        parser.process_line(
            "                         Hello, how are you?                                        "
        )

        # Check speaker was applied to dialog
        assert parser.current_chunk.speaker == "JOHN"

    def test_speaker_tracking_reset_on_dual_dialog(self, mock_logger):
        """Test speaker tracking reset on dual dialog."""
        parser = ScreenplayParser()

        # Initialize state to ACTION to ensure we're not in TITLE state
        parser.state = State.ACTION
        parser.has_left_title = True

        # Set up speaker
        parser.current_speaker = "JOHN"

        # Process dual speaker attribution
        parser.process_line(
            "                     JOHN                          MARY                            "
        )

        # Check speaker was reset
        assert parser.current_speaker == ""

    def test_speaker_tracking_preserved_across_dialog_modifier(self, mock_logger):
        """Test speaker tracking preserved across dialog modifier."""
        parser = ScreenplayParser()

        # Initialize state to ACTION to ensure we're not in TITLE state
        parser.state = State.ACTION
        parser.has_left_title = True

        # Process speaker attribution
        parser.process_line(
            "                                    JOHN                                            "
        )

        # Check speaker was tracked
        assert parser.current_speaker == "JOHN"

        # Process dialog modifier
        parser.process_line(
            "                         (pauses)                                                   "
        )

        # Check speaker is still tracked
        assert parser.current_speaker == "JOHN"

        # Process dialog
        parser.process_line(
            "                         Hello again.                                               "
        )

        # Check speaker was applied to dialog
        assert parser.current_chunk.speaker == "JOHN"
