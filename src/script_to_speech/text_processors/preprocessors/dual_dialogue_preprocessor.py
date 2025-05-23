import logging
import re
from typing import Dict, List, Literal, Tuple

from ...utils.logging import get_screenplay_logger
from ..text_preprocessor_base import TextPreProcessor

logger = get_screenplay_logger("parser.preprocessors.dual_dialogue")


class DualDialoguePreProcessor(TextPreProcessor):
    """
    Pre-processor that splits dual dialogue blocks into sequential dialogue blocks,
    handling mid-dialogue speaker transitions.
    """

    # Default minimum spacing values
    DEFAULT_MIN_SPEAKER_SPACING = 3  # Minimum spaces between speakers
    DEFAULT_MIN_DIALOGUE_SPACING = 2  # Minimum spaces between dialogue columns

    def __init__(self, config: Dict):
        """
        Initialize the DualDialoguePreProcessor with configuration.

        Args:
            config: Configuration dictionary which may contain:
                min_speaker_spacing: Minimum number of spaces between speakers
                min_dialogue_spacing: Minimum number of spaces between dialogue columns
        """
        super().__init__(config)
        # Set spacing parameters from config or use defaults
        self.min_speaker_spacing = config.get(
            "min_speaker_spacing", self.DEFAULT_MIN_SPEAKER_SPACING
        )
        self.min_dialogue_spacing = config.get(
            "min_dialogue_spacing", self.DEFAULT_MIN_DIALOGUE_SPACING
        )
        logger.debug(
            f"Initialized with min_speaker_spacing={self.min_speaker_spacing}, min_dialogue_spacing={self.min_dialogue_spacing}"
        )

    @property
    def multi_config_mode(self) -> Literal["chain", "override"]:
        """
        Override to ensure only one instance of dual dialogue processor exists.
        Last config's instance will be used if multiple configs specify this processor.
        """
        return "override"

    def validate_config(self) -> bool:
        """
        Validate the configuration.

        Returns:
            bool: True if configuration is valid, False otherwise
        """
        # Check if spacing parameters are valid integers
        if "min_speaker_spacing" in self.config and not isinstance(
            self.config["min_speaker_spacing"], int
        ):
            logger.error("min_speaker_spacing must be an integer")
            return False
        if "min_dialogue_spacing" in self.config and not isinstance(
            self.config["min_dialogue_spacing"], int
        ):
            logger.error("min_dialogue_spacing must be an integer")
            return False

        # Check if spacing parameters are positive
        if (
            "min_speaker_spacing" in self.config
            and self.config["min_speaker_spacing"] <= 0
        ):
            logger.error("min_speaker_spacing must be positive")
            return False
        if (
            "min_dialogue_spacing" in self.config
            and self.config["min_dialogue_spacing"] <= 0
        ):
            logger.error("min_dialogue_spacing must be positive")
            return False

        return True

    def _split_speakers_full(self, speaker_text: str) -> Tuple[str, str]:
        """
        Split dual speaker attribution into left and right speakers.
        Preserves parentheticals in speaker names.
        """
        parts = [
            p
            for p in re.split(r"\s{%d,}" % self.min_speaker_spacing, speaker_text)
            if p
        ]

        if len(parts) != 2:
            raise ValueError(f"Could not split speakers from: {speaker_text}")

        return parts[0], parts[1]

    def _split_dialogue(self, raw_dialogue: str) -> Tuple[List[str], List[str]]:
        """Split dual dialogue into left and right parts, preserving line structure."""
        lines = raw_dialogue.split("\n")
        left_lines = []
        right_lines = []

        logger.debug(f"\nSplitting dialogue into columns. Input lines:")
        for line in lines:
            logger.debug(f"  '{line}'")

        # Find left speaker's indentation from first line
        first_line = lines[0].rstrip()
        left_indent = len(first_line) - len(first_line.lstrip())
        logger.debug(f"Left column indent detected as: {left_indent}")

        for line in lines:
            line = line.rstrip()
            if not line:  # Skip empty lines
                logger.debug("Skipping empty line")
                continue

            # Get line's indentation
            indent = len(line) - len(line.lstrip())
            logger.debug(f"\nProcessing line with indent {indent}: '{line}'")

            if indent <= left_indent + 5:
                # This line starts at left column position or is slightly un-indented / indented
                # Split it into left and right parts
                parts = [
                    p
                    for p in re.split(r"\s{%d,}" % self.min_dialogue_spacing, line)
                    if p
                ]
                logger.debug(f"Split into parts: {parts}")
                if parts:
                    left_lines.append(parts[0])
                    logger.debug(f"Added to left: '{parts[0]}'")
                    if len(parts) > 1:
                        right_lines.append(parts[-1])
                        logger.debug(f"Added to right: '{parts[-1]}'")
            elif (
                indent > left_indent + 10
            ):  # Significantly indented, must be right speaker
                right_lines.append(line.strip())
                logger.debug(f"Added to right (indented): '{line.strip()}'")

        logger.debug("\nFinal split results:")
        logger.debug("Left lines:")
        for line in left_lines:
            logger.debug(f"  '{line}'")
        logger.debug("Right lines:")
        for line in right_lines:
            logger.debug(f"  '{line}'")

        return left_lines, right_lines

    def _process_buffer(
        self,
        lines: List[str],
        initial_speaker: str,
        speaker_raw_text: str,
        dialogue_raw_text: str,
    ) -> List[Dict]:
        """Process a buffer of lines for one column."""
        chunks = []
        current_speaker = initial_speaker
        current_buffer: List[str] = []
        current_parenthetical: List[str] = []
        in_parenthetical = False

        logger.debug(f"\nProcessing buffer for initial speaker: {initial_speaker}")
        logger.debug("Input lines:")
        for line in lines:
            logger.debug(f"  '{line}'")

        # Add initial speaker attribution
        if current_speaker:
            chunks.append(
                {
                    "type": "speaker_attribution",
                    "speaker": "",
                    "text": current_speaker,
                    "raw_text": speaker_raw_text,
                }
            )
            logger.debug(f"Added initial speaker attribution for: {current_speaker}")

        def flush_dialogue_buffer() -> None:
            if current_buffer:
                logger.debug(f"Flushing dialogue buffer for {current_speaker}:")
                for buf_line in current_buffer:
                    logger.debug(f"  '{buf_line}'")
                chunks.append(
                    {
                        "type": "dialogue",
                        "speaker": self._clean_speaker_name(current_speaker),
                        "text": " ".join(current_buffer),
                        "raw_text": dialogue_raw_text,
                    }
                )
                current_buffer.clear()
                logger.debug("Added dialogue chunk")

        def flush_parenthetical() -> None:
            if current_parenthetical:
                logger.debug("Flushing parenthetical:")
                for p_line in current_parenthetical:
                    logger.debug(f"  '{p_line}'")
                chunks.append(
                    {
                        "type": "dialogue_modifier",
                        "speaker": "",
                        "text": " ".join(current_parenthetical),
                        "raw_text": dialogue_raw_text,
                    }
                )
                current_parenthetical.clear()
                logger.debug("Added dialogue_modifier chunk")

        for line in lines:
            stripped = line.strip()
            logger.debug(f"\nProcessing line: '{stripped}'")

            if stripped.isupper() and not stripped.startswith("("):
                logger.debug(f"Found new speaker: {stripped}")
                # Found a new speaker - flush any current buffers
                flush_dialogue_buffer()
                flush_parenthetical()

                # Add speaker attribution
                chunks.append(
                    {
                        "type": "speaker_attribution",
                        "speaker": "",
                        "text": stripped,
                        "raw_text": (
                            speaker_raw_text
                            if stripped == initial_speaker
                            else dialogue_raw_text
                        ),
                    }
                )
                logger.debug(f"Added speaker attribution for: {stripped}")

                # Set new speaker
                current_speaker = stripped
            elif stripped.startswith("("):
                logger.debug("Found parenthetical")
                # If we were in the middle of dialogue, flush it
                flush_dialogue_buffer()

                if stripped.endswith(")"):
                    # Single-line parenthetical
                    logger.debug("Single-line parenthetical")
                    chunks.append(
                        {
                            "type": "dialogue_modifier",
                            "speaker": "",
                            "text": stripped,
                            "raw_text": dialogue_raw_text,
                        }
                    )
                    logger.debug(f"Added dialogue_modifier: {stripped}")
                else:
                    # Start of multi-line parenthetical
                    logger.debug("Starting multi-line parenthetical")
                    in_parenthetical = True
                    current_parenthetical.append(stripped)
            elif stripped.endswith(")") and in_parenthetical:
                logger.debug("Ending multi-line parenthetical")
                current_parenthetical.append(stripped)
                flush_parenthetical()
                in_parenthetical = False
            elif in_parenthetical:
                logger.debug("Continuing parenthetical")
                current_parenthetical.append(stripped)
            else:
                logger.debug("Adding to dialogue buffer")
                current_buffer.append(stripped)

        # Flush any remaining buffers
        flush_dialogue_buffer()
        flush_parenthetical()

        return chunks

    def _clean_speaker_name(self, name: str) -> str:
        """Remove parentheticals and whitespace from speaker name."""
        return re.sub(r"\([^)]*\)", "", name).strip()

    def _process_dual_dialogue_pair(
        self, speaker_chunk: Dict, dialogue_chunk: Dict
    ) -> List[Dict]:
        """Process a pair of dual speaker attribution and dual dialogue chunks."""
        # Get initial left and right speakers
        left_speaker, right_speaker = self._split_speakers_full(speaker_chunk["text"])
        logger.debug(
            f"\nProcessing dual dialogue pair with speakers: {left_speaker} | {right_speaker}"
        )

        # Split dialogue into columns
        left_lines, right_lines = self._split_dialogue(dialogue_chunk["raw_text"])

        # Process each column
        result_chunks = []

        # Process left buffer
        logger.debug("\nProcessing left column...")
        result_chunks.extend(
            self._process_buffer(
                left_lines,
                left_speaker,
                speaker_chunk["raw_text"],
                dialogue_chunk["raw_text"],
            )
        )

        # Process right buffer
        logger.debug("\nProcessing right column...")
        result_chunks.extend(
            self._process_buffer(
                right_lines,
                right_speaker,
                speaker_chunk["raw_text"],
                dialogue_chunk["raw_text"],
            )
        )

        return result_chunks

    def process(self, chunks: List[Dict]) -> Tuple[List[Dict], bool]:
        """Process chunks by converting dual dialogue into sequential dialogue."""
        if not chunks:
            return chunks, False

        result_chunks = []
        i = 0
        made_changes = False

        while i < len(chunks):
            current_chunk = chunks[i]

            # Look for dual speaker attribution
            if current_chunk["type"] == "dual_speaker_attribution" and i + 1 < len(
                chunks
            ):
                next_chunk = chunks[i + 1]

                # Check if followed by dual dialogue
                if next_chunk["type"] == "dual_dialogue":
                    made_changes = True
                    # Process the dual dialogue pair and create individual dialogue chunks
                    new_chunks = self._process_dual_dialogue_pair(
                        current_chunk, next_chunk
                    )
                    result_chunks.extend(new_chunks)
                    i += 2  # Skip both chunks
                    continue

            # Keep non-dual-dialogue chunks as is
            result_chunks.append(current_chunk)
            i += 1

        return result_chunks, made_changes
