"""
Unit tests for the screenplay_parser module.

This module contains comprehensive tests for the screenplay_parser.py module,
focusing on the core parser functionality, state detection, and chunk generation.
"""

import json
import re
from unittest.mock import MagicMock, mock_open, patch

import pytest

from script_to_speech.parser.screenplay_parser import (
    Chunk,
    IndentationContext,
    ParserConfig,
    ScreenplayParser,
    State,
)


class TestFullParsing:
    """Tests for full screenplay parsing."""

    @pytest.fixture
    def mock_logger(self):
        """Fixture to mock the logger."""
        with patch("script_to_speech.parser.screenplay_parser.logger") as mock:
            yield mock

    def test_parse_screenplay_empty(self, mock_logger):
        """Test parsing empty screenplay."""
        parser = ScreenplayParser()

        # Parse empty text
        chunks = parser.parse_screenplay("")

        # Should have no chunks
        assert chunks == []

    def test_parse_screenplay_basic(self, mock_logger):
        """Test parsing basic screenplay."""
        parser = ScreenplayParser()

        # Basic screenplay text
        text = """TITLE

INT. LIVING ROOM - DAY

John enters the room.
"""

        # Parse text
        chunks = parser.parse_screenplay(text)

        # Should have 3 chunks: action (TITLE), scene heading, action
        assert len(chunks) == 3
        assert chunks[0]["type"] == "action"  # TITLE is parsed as action
        assert chunks[0]["text"] == "TITLE"
        assert chunks[1]["type"] == "scene_heading"
        assert chunks[2]["type"] == "action"

    def test_parse_screenplay_with_dialogue(self, mock_logger):
        """Test parsing screenplay with dialogue."""
        parser = ScreenplayParser()

        # Screenplay text with dialogue
        text = """INT. LIVING ROOM - DAY

John enters the room.

                                    JOHN
                                    
                         Hello, how are you?
                         
Mary looks up.

                                    MARY
                                    
                         I'm fine, thank you.
"""

        # Parse text
        chunks = parser.parse_screenplay(text)

        # Should have 7 chunks: scene heading, action, speaker, dialogue, action, speaker, dialogue
        assert len(chunks) == 7
        assert chunks[0]["type"] == "scene_heading"
        assert chunks[1]["type"] == "action"
        assert chunks[2]["type"] == "speaker_attribution"
        assert chunks[3]["type"] == "dialogue"
        assert chunks[3]["speaker"] == "JOHN"
        assert chunks[4]["type"] == "action"
        assert chunks[5]["type"] == "speaker_attribution"
        assert chunks[6]["type"] == "dialogue"
        assert chunks[6]["speaker"] == "MARY"

    def test_parse_screenplay_with_dual_dialogue(self, mock_logger):
        """Test parsing screenplay with dual dialogue."""
        parser = ScreenplayParser()

        # Screenplay text with dual dialogue
        text = """INT. LIVING ROOM - DAY

John and Mary speak simultaneously.

                     JOHN                          MARY
                     
               Hello!                         Hi there!
               
               How are you?                   I'm good!
"""

        # Parse text
        chunks = parser.parse_screenplay(text)

        # Should have 4 chunks: scene heading, action, dual speaker, action (dual dialogue)
        assert len(chunks) == 4
        assert chunks[0]["type"] == "scene_heading"
        assert chunks[1]["type"] == "action"
        assert chunks[2]["type"] == "dual_speaker_attribution"
        assert chunks[3]["type"] == "action"  # Dual dialogue is parsed as action
        assert "Hello!" in chunks[3]["text"]
        assert "Hi there!" in chunks[3]["text"]

    def test_parse_screenplay_with_page_numbers(self, mock_logger):
        """Test parsing screenplay with page numbers."""
        parser = ScreenplayParser()

        # Screenplay text with page numbers
        text = """INT. LIVING ROOM - DAY

John enters the room.

                                                                 2.
                                                                 
EXT. GARDEN - DAY

Mary waters the plants.
"""

        # Parse text
        chunks = parser.parse_screenplay(text)

        # Should have 5 chunks: scene heading, action, page number, scene heading, action
        assert len(chunks) == 5
        assert chunks[0]["type"] == "scene_heading"
        assert chunks[1]["type"] == "action"
        assert chunks[2]["type"] == "page_number"
        assert chunks[3]["type"] == "scene_heading"
        assert chunks[4]["type"] == "action"

    def test_parse_screenplay_with_dialogue_modifiers(self, mock_logger):
        """Test parsing screenplay with dialogue modifiers."""
        parser = ScreenplayParser()

        # Screenplay text with dialogue modifiers
        text = """INT. LIVING ROOM - DAY

                                    JOHN
                                    
                         Hello there.
                         
                         (pauses)
                         
                         How are you today?
"""

        # Parse text
        chunks = parser.parse_screenplay(text)

        # Should have 5 chunks: scene heading, speaker, dialogue, dialogue modifier, dialogue
        assert len(chunks) == 5
        assert chunks[0]["type"] == "scene_heading"
        assert chunks[1]["type"] == "speaker_attribution"
        assert chunks[2]["type"] == "dialogue"
        assert chunks[3]["type"] == "dialogue_modifier"
        assert chunks[4]["type"] == "dialogue"
        assert chunks[4]["speaker"] == "JOHN"

    def test_parse_screenplay_with_multiline_dialogue_modifiers(self, mock_logger):
        """Test parsing screenplay with multi-line dialogue modifiers."""
        parser = ScreenplayParser()

        # Screenplay text with multi-line dialogue modifier (based on provided example)
        text = """INT. KITCHEN - DAY

                                  TRUCKDRIVER                                       
                        We gotta bust outta here ...  git                           
                        to where there's some folks ...                             
                        somebody with guns or                                       
                        somethin ... .                                              
                            (He quickly moves toward the                            
                            kitchen.)                                               
                        I'll try to scare up some grub.
"""

        # Parse text
        chunks = parser.parse_screenplay(text)

        # Should have 5 chunks: scene_heading, speaker, dialogue, dialogue_modifier, dialogue
        assert len(chunks) == 5
        assert chunks[0]["type"] == "scene_heading"
        assert chunks[1]["type"] == "speaker_attribution"
        assert chunks[1]["text"] == "TRUCKDRIVER"

        assert chunks[2]["type"] == "dialogue"
        assert chunks[2]["speaker"] == "TRUCKDRIVER"
        expected_dialogue1 = "We gotta bust outta here ...  git to where there's some folks ... somebody with guns or somethin ... ."
        assert chunks[2]["text"] == expected_dialogue1

        assert chunks[3]["type"] == "dialogue_modifier"
        expected_modifier = "(He quickly moves toward the kitchen.)"
        assert chunks[3]["text"] == expected_modifier

        assert chunks[4]["type"] == "dialogue"
        assert chunks[4]["speaker"] == "TRUCKDRIVER"
        assert chunks[4]["text"] == "I'll try to scare up some grub."

    def test_parse_screenplay_dialogue_modifier_regression(self, mock_logger):
        """Test that dialogue modifiers don't capture subsequent speaker attributions."""
        parser = ScreenplayParser()

        # Screenplay text that reproduces the regression from multi_line_2.txt
        text = """INT. LIVING ROOM - DAY

                                   ALICE                                             
                         It doesn't work that way, kid.                           
                         You don't know me.                             
                                                                                    
                                                                (CONTINUED)         
                                                                                    
               CONTINUED: (2)                                                       
                                                                                    
                                   CAT                                             
                         You don't know anything about me!                          
                                                                                    
                                   ALICE                                             
                         I know enough.
"""

        # Parse text
        chunks = parser.parse_screenplay(text)

        # Should have 9 chunks total
        assert len(chunks) == 9

        # Verify the structure matches expected output
        assert chunks[0]["type"] == "scene_heading"

        assert chunks[1]["type"] == "speaker_attribution"
        assert chunks[1]["text"] == "ALICE"

        assert chunks[2]["type"] == "dialogue"
        assert chunks[2]["speaker"] == "ALICE"
        expected_alice_dialogue1 = "It doesn't work that way, kid. You don't know me."
        assert chunks[2]["text"] == expected_alice_dialogue1

        assert chunks[3]["type"] == "dialogue_modifier"
        assert chunks[3]["text"] == "(CONTINUED)"

        assert chunks[4]["type"] == "action"
        assert chunks[4]["text"] == "CONTINUED: (2)"

        assert chunks[5]["type"] == "speaker_attribution"
        assert chunks[5]["text"] == "CAT"

        assert chunks[6]["type"] == "dialogue"
        assert chunks[6]["speaker"] == "CAT"
        assert chunks[6]["text"] == "You don't know anything about me!"

        assert chunks[7]["type"] == "speaker_attribution"
        assert chunks[7]["text"] == "ALICE"

        assert chunks[8]["type"] == "dialogue"
        assert chunks[8]["speaker"] == "ALICE"
        assert chunks[8]["text"] == "I know enough."

    @pytest.mark.integration
    @patch("builtins.open", new_callable=mock_open)
    def test_parse_real_world_example(self, mock_file_open, mock_logger):
        """Test parsing a real-world screenplay example."""
        parser = ScreenplayParser()

        # Mock JSON data
        mock_json_data = [
            {
                "type": "title",
                "text": "A COMPLETE UNKNOWN",
                "raw_text": "A COMPLETE UNKNOWN",
            },
            {
                "type": "scene_heading",
                "text": "INT. CAFE - DAY",
                "raw_text": "INT. CAFE - DAY",
            },
            {
                "type": "action",
                "text": "Bob sits at a table.",
                "raw_text": "Bob sits at a table.",
            },
        ]

        # Set up mock file content
        mock_file_open.return_value.__enter__.return_value.read.return_value = (
            json.dumps(mock_json_data)
        )

        # Create a simplified screenplay text from the chunks
        text = ""
        for chunk in mock_json_data:
            text += chunk["raw_text"] + "\n\n"

        # Parse text
        chunks = parser.parse_screenplay(text)

        # Should have similar structure to the original
        assert len(chunks) > 0

        # Check that we have various chunk types
        chunk_types = [chunk["type"] for chunk in chunks]
        assert "action" in chunk_types
        assert "scene_heading" in chunk_types
