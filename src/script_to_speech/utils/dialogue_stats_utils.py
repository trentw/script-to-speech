"""
Utility functions for calculating dialogue statistics (line counts, character counts, etc.)
from screenplay dialogue data.
"""

from collections import Counter
from typing import Dict, List, NamedTuple, TypedDict


class SpeakerStats(NamedTuple):
    """Statistics for a single speaker."""

    line_count: int
    total_characters: int
    longest_dialogue: int


class DialogueStatsDict(TypedDict):
    """Type definition for dialogue statistics dictionary."""

    line_count: int
    total_characters: int
    longest_dialogue: int


def resolve_speaker_name(speaker: str) -> str:
    """
    Resolve speaker name, treating empty/None speakers as 'default'.

    Args:
        speaker: The speaker name from dialogue chunk

    Returns:
        str: The resolved speaker name ('default' for empty/None speakers)
    """
    return speaker if speaker else "default"


def speaker_matches_target(dialogue_speaker: str, target_speaker: str) -> bool:
    """
    Check if a dialogue chunk's speaker matches the target speaker.
    Handles the special case where empty/None speakers match 'default'.

    Args:
        dialogue_speaker: Speaker from dialogue chunk (may be None/empty)
        target_speaker: The speaker we're checking against

    Returns:
        bool: True if the speakers match
    """
    return dialogue_speaker == target_speaker or (
        not dialogue_speaker and target_speaker == "default"
    )


def analyze_speaker_lines(dialogues: List[Dict]) -> Dict[str, int]:
    """
    Analyze list of dialogue chunks to count speaker lines.
    'default' speaker is used for chunks with no speaker attribute.
    Returns counts with 'default' first, followed by other speakers sorted by frequency.

    Args:
        dialogues: List of dialogue chunks

    Returns:
        Dict[str, int]: Ordered dict with speaker names as keys and line counts as values
    """
    counts: Counter[str] = Counter()
    default_count = 0

    for dialogue in dialogues:
        if dialogue["type"] == "dialogue":
            speaker = dialogue.get("speaker")
            if speaker:
                counts[speaker] += 1
            else:
                default_count += 1
        else:
            # Non-dialogue chunks use default speaker
            default_count += 1

    # Create ordered dict with default first
    result = {"default": default_count}

    # Add other speakers sorted by count (descending) then name
    for speaker, count in sorted(counts.items(), key=lambda x: (-x[1], x[0])):
        result[speaker] = count

    return result


def calculate_speaker_character_stats(
    dialogues: List[Dict], speaker: str
) -> DialogueStatsDict:
    """
    Calculate character statistics for a specific speaker.

    Args:
        dialogues: List of dialogue chunks
        speaker: The speaker to calculate stats for

    Returns:
        DialogueStatsDict: Dictionary containing total_characters and longest_dialogue
    """

    def should_include_dialogue(dialogue: Dict) -> bool:
        """Determine if this dialogue should be included for the target speaker."""
        if speaker == "default":
            # Default speaker gets: non-dialogue chunks OR dialogue chunks without speaker
            return dialogue["type"] != "dialogue" or not dialogue.get("speaker")
        else:
            # Named speakers only get dialogue chunks with matching speaker
            return dialogue["type"] == "dialogue" and dialogue.get("speaker") == speaker

    total_chars = sum(
        len(str(dialogue.get("text", "")))
        for dialogue in dialogues
        if should_include_dialogue(dialogue)
    )

    longest_dialogue = max(
        (
            len(str(dialogue.get("text", "")))
            for dialogue in dialogues
            if should_include_dialogue(dialogue)
        ),
        default=0,
    )

    return {
        "line_count": sum(
            1 for dialogue in dialogues if should_include_dialogue(dialogue)
        ),
        "total_characters": total_chars,
        "longest_dialogue": longest_dialogue,
    }


def get_speaker_statistics(dialogues: List[Dict]) -> Dict[str, SpeakerStats]:
    """
    Get comprehensive statistics for all speakers in dialogue chunks.
    Combines line counts and character statistics in a single pass for efficiency.

    Args:
        dialogues: List of dialogue chunks

    Returns:
        Dict[str, SpeakerStats]: Dictionary mapping speaker names to their statistics
    """
    # First get line counts using existing function
    line_counts = analyze_speaker_lines(dialogues)

    # Initialize character tracking for all speakers
    char_counts = {speaker: 0 for speaker in line_counts}
    max_dialogue_lengths = {speaker: 0 for speaker in line_counts}

    # Single pass through dialogues to calculate character stats
    for dialogue in dialogues:
        text = str(dialogue.get("text", ""))
        text_length = len(text)
        dialogue_speaker = dialogue.get("speaker")

        # Determine which speaker this dialogue belongs to
        if dialogue["type"] == "dialogue" and dialogue_speaker:
            # Normal dialogue with speaker
            target_speaker = dialogue_speaker
        else:
            # Non-dialogue chunks or dialogue without speaker go to default
            target_speaker = "default"

        # Update character count and max dialogue length for the target speaker
        if target_speaker in char_counts:
            char_counts[target_speaker] += text_length
            max_dialogue_lengths[target_speaker] = max(
                max_dialogue_lengths[target_speaker], text_length
            )

    # Combine all statistics
    return {
        speaker: SpeakerStats(
            line_count=line_counts[speaker],
            total_characters=char_counts[speaker],
            longest_dialogue=max_dialogue_lengths[speaker],
        )
        for speaker in line_counts
    }


def get_all_speaker_names(dialogues: List[Dict]) -> List[str]:
    """
    Get all unique speaker names from dialogue chunks, including 'default'.

    Args:
        dialogues: List of dialogue chunks

    Returns:
        List[str]: List of unique speaker names, with 'default' first
    """
    speakers = set()
    has_default = False

    for dialogue in dialogues:
        if dialogue["type"] == "dialogue":
            speaker = dialogue.get("speaker")
            if speaker:
                speakers.add(speaker)
            else:
                has_default = True
        else:
            # Non-dialogue chunks use default speaker
            has_default = True

    result = []
    if has_default:
        result.append("default")

    # Add other speakers sorted alphabetically
    result.extend(sorted(speakers))

    return result
