"""
Test dialogue statistics utility functions.
"""

import pytest

from script_to_speech.utils.dialogue_stats_utils import (
    SpeakerStats,
    analyze_speaker_lines,
    calculate_speaker_character_stats,
    get_all_speaker_names,
    get_speaker_statistics,
    resolve_speaker_name,
    speaker_matches_target,
)


class TestDialogueStatsUtils:
    """Test dialogue statistics utility functions."""

    @pytest.fixture
    def sample_dialogues(self):
        """Sample dialogue data for testing."""
        return [
            {"type": "dialogue", "speaker": "John", "text": "Hello world"},
            {"type": "dialogue", "speaker": "Jane", "text": "Hi there, how are you?"},
            {"type": "dialogue", "speaker": None, "text": "Some narrator text"},
            {"type": "scene_description", "text": "Scene description here"},
            {
                "type": "dialogue",
                "speaker": "John",
                "text": "Another line for John with more text",
            },
            {"type": "dialogue", "speaker": "", "text": "Empty speaker dialogue"},
        ]

    def test_resolve_speaker_name(self):
        """Test speaker name resolution."""
        assert resolve_speaker_name("John") == "John"
        assert resolve_speaker_name("") == "default"
        assert resolve_speaker_name(None) == "default"

    def test_speaker_matches_target(self):
        """Test speaker matching logic."""
        # Normal speaker matching
        assert speaker_matches_target("John", "John") is True
        assert speaker_matches_target("John", "Jane") is False

        # Default speaker matching
        assert speaker_matches_target(None, "default") is True
        assert speaker_matches_target("", "default") is True
        assert speaker_matches_target("John", "default") is False

        # Edge cases
        assert speaker_matches_target(None, "John") is False
        assert speaker_matches_target("", "John") is False

    def test_analyze_speaker_lines(self, sample_dialogues):
        """Test speaker line counting."""
        result = analyze_speaker_lines(sample_dialogues)

        expected = {
            "default": 3,  # None speaker, scene_description, empty speaker
            "John": 2,  # Two John dialogues
            "Jane": 1,  # One Jane dialogue
        }

        assert result == expected

        # Verify ordering: default first, then by frequency (descending), then alphabetically
        assert list(result.keys()) == ["default", "John", "Jane"]

    def test_analyze_speaker_lines_empty(self):
        """Test speaker line counting with empty input."""
        result = analyze_speaker_lines([])
        assert result == {"default": 0}

    def test_analyze_speaker_lines_no_dialogue(self):
        """Test speaker line counting with no dialogue chunks."""
        dialogues = [
            {"type": "scene_description", "text": "Scene 1"},
            {"type": "action", "text": "Action happens"},
        ]
        result = analyze_speaker_lines(dialogues)
        assert result == {"default": 2}

    def test_calculate_speaker_character_stats(self, sample_dialogues):
        """Test character statistics calculation for specific speaker."""
        # Test John's stats
        john_stats = calculate_speaker_character_stats(sample_dialogues, "John")
        expected_john = {
            "line_count": 2,  # Two John dialogues
            "total_characters": 47,  # "Hello world" (11) + "Another line for John with more text" (36)
            "longest_dialogue": 36,  # "Another line for John with more text"
        }
        assert john_stats == expected_john

        # Test Jane's stats
        jane_stats = calculate_speaker_character_stats(sample_dialogues, "Jane")
        expected_jane = {
            "line_count": 1,  # One Jane dialogue
            "total_characters": 22,  # "Hi there, how are you?" (22)
            "longest_dialogue": 22,  # "Hi there, how are you?"
        }
        assert jane_stats == expected_jane

        # Test default speaker stats (includes None, empty, and non-dialogue)
        default_stats = calculate_speaker_character_stats(sample_dialogues, "default")
        expected_default = {
            "line_count": 3,  # None speaker, scene_description, empty speaker
            "total_characters": 62,  # "Some narrator text" (18) + "Scene description here" (22) + "Empty speaker dialogue" (22)
            "longest_dialogue": 22,  # Multiple items with this length
        }
        assert default_stats == expected_default

    def test_calculate_speaker_character_stats_nonexistent_speaker(
        self, sample_dialogues
    ):
        """Test character stats for non-existent speaker."""
        stats = calculate_speaker_character_stats(sample_dialogues, "NonExistent")
        assert stats == {"line_count": 0, "total_characters": 0, "longest_dialogue": 0}

    def test_get_speaker_statistics(self, sample_dialogues):
        """Test comprehensive speaker statistics."""
        all_stats = get_speaker_statistics(sample_dialogues)

        # Check that all expected speakers are present
        assert set(all_stats.keys()) == {"default", "John", "Jane"}

        # Check John's complete stats
        john_stats = all_stats["John"]
        assert isinstance(john_stats, SpeakerStats)
        assert john_stats.line_count == 2
        assert john_stats.total_characters == 47
        assert john_stats.longest_dialogue == 36

        # Check Jane's complete stats
        jane_stats = all_stats["Jane"]
        assert jane_stats.line_count == 1
        assert jane_stats.total_characters == 22
        assert jane_stats.longest_dialogue == 22

        # Check default speaker stats
        default_stats = all_stats["default"]
        assert default_stats.line_count == 3
        assert default_stats.total_characters == 62
        assert default_stats.longest_dialogue == 22

    def test_get_speaker_statistics_empty(self):
        """Test comprehensive stats with empty input."""
        result = get_speaker_statistics([])
        assert result == {
            "default": SpeakerStats(
                line_count=0, total_characters=0, longest_dialogue=0
            )
        }

    def test_get_all_speaker_names(self, sample_dialogues):
        """Test getting all unique speaker names."""
        result = get_all_speaker_names(sample_dialogues)

        # Should include default first, then others alphabetically
        assert result == ["default", "Jane", "John"]

    def test_get_all_speaker_names_no_default(self):
        """Test getting speaker names when no default is needed."""
        dialogues = [
            {"type": "dialogue", "speaker": "John", "text": "Hello"},
            {"type": "dialogue", "speaker": "Jane", "text": "Hi"},
        ]
        result = get_all_speaker_names(dialogues)
        assert result == ["Jane", "John"]

    def test_get_all_speaker_names_only_default(self):
        """Test getting speaker names when only default is present."""
        dialogues = [
            {"type": "scene_description", "text": "Scene"},
            {"type": "dialogue", "speaker": None, "text": "Narrator"},
        ]
        result = get_all_speaker_names(dialogues)
        assert result == ["default"]

    def test_speaker_stats_named_tuple(self):
        """Test SpeakerStats named tuple functionality."""
        stats = SpeakerStats(line_count=5, total_characters=100, longest_dialogue=25)

        # Test field access
        assert stats.line_count == 5
        assert stats.total_characters == 100
        assert stats.longest_dialogue == 25

        # Test tuple unpacking
        line_count, total_chars, longest = stats
        assert line_count == 5
        assert total_chars == 100
        assert longest == 25

    def test_consistency_between_functions(self, sample_dialogues):
        """Test that individual functions produce consistent results with comprehensive function."""
        # Get results from individual functions
        line_counts = analyze_speaker_lines(sample_dialogues)

        # Get results from comprehensive function
        all_stats = get_speaker_statistics(sample_dialogues)

        # Verify line counts match
        for speaker in line_counts:
            assert line_counts[speaker] == all_stats[speaker].line_count

        # Verify character stats match for each speaker
        for speaker in line_counts:
            individual_char_stats = calculate_speaker_character_stats(
                sample_dialogues, speaker
            )
            comprehensive_stats = all_stats[speaker]

            assert (
                individual_char_stats["total_characters"]
                == comprehensive_stats.total_characters
            )
            assert (
                individual_char_stats["longest_dialogue"]
                == comprehensive_stats.longest_dialogue
            )
