import re
from collections import OrderedDict
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Pattern

from ..utils.logging import get_screenplay_logger

logger = get_screenplay_logger("parser.screenplay")


@dataclass
class ParserConfig:
    """Configuration parameters for screenplay parsing."""

    # Indentation level constants
    speaker_indent_min: int = 30  # Minimum indentation for speaker attribution
    speaker_indent_max: int = 45  # Maximum indentation for speaker attribution
    dialogue_indent_min: int = 20  # Minimum indentation for dialogue blocks
    dialogue_indent_max: int = 29  # Maximum indentation for dialogue blocks
    dual_speaker_min_speaker_spacing: int = 8  # Minimum spaces between dual speakers
    dual_speaker_min_dialogue_spacing: int = (
        2  # Minimum spaces between blocks of dual dialogue
    )

    # Pattern caching
    _dual_speaker_pattern: Optional[Pattern] = field(
        default=None, repr=False, compare=False
    )
    _scene_heading_pattern: Optional[Pattern] = field(
        default=None, repr=False, compare=False
    )

    def get_dual_speaker_pattern(self) -> Pattern:
        """Get or compile the dual speaker pattern."""
        if self._dual_speaker_pattern is None:
            self._dual_speaker_pattern = re.compile(
                rf"([A-Z][A-Z0-9#,\.\(\)'\-]*(?:\s+[A-Z0-9#,\.\(\)'\-]+)*)"
                rf"\s{{{self.dual_speaker_min_speaker_spacing},}}"
                rf"([A-Z][A-Z0-9#,\.\(\)'\-]*(?:\s+[A-Z0-9#,\.\(\)'\-]+)*)"
            )
        return self._dual_speaker_pattern

    def get_scene_heading_pattern(self) -> Pattern:
        """Get or compile the scene heading pattern."""
        if self._scene_heading_pattern is None:
            self._scene_heading_pattern = re.compile(
                r"^\s*(?:[A-Z]?\d+(?:\.\d+)?[A-Z]?\s+)?(INT\.|EXT\.)"
            )
        return self._scene_heading_pattern


class State(Enum):
    TITLE = auto()
    SCENE_HEADING = auto()
    ACTION = auto()
    SPEAKER_ATTRIBUTION = auto()
    DIALOGUE = auto()
    DIALOGUE_MODIFIER = auto()
    DUAL_SPEAKER_ATTRIBUTION = auto()
    DUAL_DIALOGUE = auto()
    PAGE_NUMBER = auto()  # New state for page numbers


@dataclass
class Chunk:
    """Represents a parsed chunk of screenplay text."""

    type: str  # State name in snake_case
    speaker: Optional[str] = None  # Speaker name, None, or empty string
    raw_text: str = ""  # Original text with formatting
    text: str = ""  # Cleaned text


@dataclass
class IndentationContext:
    """Tracks indentation context during screenplay parsing."""

    last_speaker_indent: Optional[int] = None
    last_dialogue_indent: Optional[int] = None
    last_action_indent: Optional[int] = None
    current_indent: Optional[int] = None

    def update(self, state: State, indent: int) -> None:
        """
        Update indentation context based on current state and indentation.

        Args:
            state: Current state
            indent: Current line indentation
        """
        self.current_indent = indent
        if state == State.SPEAKER_ATTRIBUTION:
            self.last_speaker_indent = indent
        elif state == State.DIALOGUE:
            self.last_dialogue_indent = indent
        elif state == State.ACTION:
            self.last_action_indent = indent


class ScreenplayParser:
    """Parser for screenplay text using a probabilistic state machine approach."""

    def __init__(self, config: Optional[ParserConfig] = None):
        """
        Initialize the screenplay parser.

        Args:
            config: Optional parser configuration. Default configuration used if not provided.
        """
        self.config = config or ParserConfig()
        self.state = State.TITLE  # Start in TITLE state
        self.has_left_title = False
        self.current_speaker = ""  # Empty string instead of 'none'
        self.current_chunk: Optional[Chunk] = None
        self.chunks: List[Chunk] = []
        self.indent_context = IndentationContext()
        self.prev_line = ""
        self.prev_non_empty_line = ""

    def state_to_type(self, state: State) -> str:
        """
        Convert state enum to snake_case string.

        Args:
            state: State enum value

        Returns:
            String representation of state in snake_case
        """
        return state.name.lower()

    def clean_speaker_name(self, text: str) -> str:
        """
        Remove parentheticals and whitespace from speaker name.

        Args:
            text: Raw speaker text

        Returns:
            Cleaned speaker name
        """
        return re.sub(r"\([^)]*\)", "", text).strip()

    def calculate_probabilities(
        self,
        line: str,
        indentation: int,
        current_state: State,
        has_left_title: bool,
        current_speaker: str,
        indent_context: IndentationContext,
        prev_line: str,
        prev_non_empty_line: str,
    ) -> Dict[State, float]:
        """
        Calculate probability scores for each possible state.

        Args:
            line: Current line of text
            indentation: Indentation level of current line
            current_state: Current parsing state
            has_left_title: Whether we've left the title state
            current_speaker: Current speaker name or empty string
            indent_context: Indentation context tracking object
            prev_line: Previous line of text
            prev_non_empty_line: Previous non-empty line of text

        Returns:
            Dictionary mapping states to their probability scores
        """
        # Initialize all states with base probability (0.1)
        probs = {state: 0.1 for state in State}

        # Title state starts very high (2.0) to catch initial title block
        # Sets to 0 once we've left title state
        probs[State.TITLE] = 2.0 if not has_left_title else 0.0

        stripped = line.strip()
        prev_line_blank = not prev_line.strip()
        logger.debug(f"\nCalculating probabilities for line: {stripped[:40]}...")
        logger.debug(f"Current state: {current_state}")
        logger.debug(f"Indentation: {indentation}")

        # Page number detection (super high probability if it's a page number)
        if self.is_page_number(line):
            probs[State.PAGE_NUMBER] = 5.0
            return probs  # Early return for page numbers

        # Dual speaker detection
        # Very high probability (1.0) when we see two speakers with sufficient spacing
        if self.is_dual_speaker(line, indentation):
            probs[State.DUAL_SPEAKER_ATTRIBUTION] += 1.0
            logger.debug("Detected potential dual speaker attribution")

        # Dual dialogue handling
        # Reset to base probability on blank lines
        # High probability (0.8) for less indented dialogue lines
        # Significant penalty (-0.8) to action detection in dual dialogue
        if current_state in [State.DUAL_SPEAKER_ATTRIBUTION, State.DUAL_DIALOGUE]:
            internal_spacing = self.get_max_internal_spacing(stripped)
            non_second_speaker_check = indentation < (len(line) / 2)
            text_beyond_halway_of_line_check = len(line.strip()) + indentation > (
                len(line) / 2
            )

            logger.debug(f"Dual dialogue max internal spacing: {internal_spacing}")
            logger.debug(f"Non-second speaker indentation: {non_second_speaker_check}")
            logger.debug(
                f"Text beyond halfway in line: {text_beyond_halway_of_line_check}"
            )
            logger.debug(f"Previous line blank: {prev_line_blank}")

            if prev_line_blank or (
                internal_spacing < self.config.dual_speaker_min_dialogue_spacing
                and non_second_speaker_check
                and text_beyond_halway_of_line_check
            ):
                # Reset dual dialogue probability if:
                # The last line was a blank line
                # OR the line has less than the minimum spacing between speakers AND the indentation looks like a scene header (and not the 2nd speaker) AND the text extends beyond half way across the page
                probs[State.DUAL_DIALOGUE] = 0.1  # Back to baseline
                logger.debug("Resetting dual dialogue probability to baseline")
            elif indentation < self.config.dialogue_indent_min or indentation > (
                len(line) / 2
            ):
                probs[State.DUAL_DIALOGUE] += 0.8
                probs[State.ACTION] -= 0.8

        # Relative indentation effects
        # Moderate boost (0.4) for maintaining same dialogue indentation
        # Strong action boost (0.6) and slight dialogue penalty (-0.1) for significant dedent
        if indent_context.last_dialogue_indent is not None:
            indent_change = indentation - indent_context.last_dialogue_indent
            if abs(indent_change) <= 2:
                probs[State.DIALOGUE] += 0.4
            elif indent_change < -5:
                probs[State.ACTION] += 0.6
                probs[State.DIALOGUE] -= 0.1

        # Dialogue modifier detection
        # Strong continuation probability (0.7) while in modifier state
        # High probability (0.9) for complete single-line parenthetical
        # Good probability (0.7) for start of multi-line parenthetical
        if (
            current_state == State.DIALOGUE_MODIFIER
            and not prev_non_empty_line.strip().endswith(")")
        ):
            probs[State.DIALOGUE_MODIFIER] += 0.9
        elif self.is_dialogue_modifier(line):
            if current_state in [State.DIALOGUE, State.SPEAKER_ATTRIBUTION]:
                if stripped.startswith("(") or stripped.endswith(")"):
                    probs[State.DIALOGUE_MODIFIER] += 0.9
                else:
                    probs[State.DIALOGUE_MODIFIER] += 0.7

        # Speaker attribution
        # Strong base probability (0.6) for properly indented speaker names
        # Additional boost (0.2) when coming from action block
        if self.is_speaker_attribution(line, indentation):
            probs[State.SPEAKER_ATTRIBUTION] += 0.6
            if current_state == State.ACTION:
                probs[State.SPEAKER_ATTRIBUTION] += 0.2

        # Right-aligned action blocks (CUT TO:, etc.)
        # Probability boost when we have an all-caps, non-scene header block indented far more than
        # a speaker attribution
        if self.is_right_aligned_action(line, indentation):
            probs[State.ACTION] += 0.8

        # Dialogue indicators
        # Moderate probability boost (0.4) for properly indented lines with speaker
        # Additional boost (0.3) after speaker attribution or dialogue modifier
        if current_speaker:
            if (
                self.config.dialogue_indent_min
                <= indentation
                < self.config.dialogue_indent_max
            ):
                probs[State.DIALOGUE] += 0.4
                if current_state == State.SPEAKER_ATTRIBUTION:
                    probs[State.DIALOGUE] += 0.3
                elif current_state == State.DIALOGUE_MODIFIER:
                    probs[State.DIALOGUE] += 0.3

        # Action state
        # Moderate base probability (0.4) for less indented lines
        # Additional boost (0.3) when dedenting from dialogue
        # Slight dialogue penalty (-0.2) when dedenting
        if indentation < self.config.dialogue_indent_min:
            probs[State.ACTION] += 0.4
            if (
                current_state == State.DIALOGUE
                and indent_context.last_dialogue_indent is not None
            ):
                if indentation < indent_context.last_dialogue_indent:
                    probs[State.ACTION] += 0.3
                    probs[State.DIALOGUE] -= 0.2
            probs[State.TITLE] = 0.0  # Exit title state

        # Scene heading detection
        # High probability (0.8) for INT./EXT. markers
        if self.is_scene_heading(line):
            probs[State.SCENE_HEADING] += 0.8
            probs[State.DUAL_SPEAKER_ATTRIBUTION] = 0.1
            probs[State.ACTION] = 0.1
            probs[State.TITLE] = 0.0  # Exit title state

        # Log final probabilities at debug level
        for state, prob in sorted(probs.items(), key=lambda x: x[1], reverse=True):
            logger.debug(f"{state.name}: {prob:.2f}")

        return probs

    def determine_state(self, line: str, indentation: int) -> Optional[State]:
        """
        Determine state based on probability calculations.

        Args:
            line: Current line of text
            indentation: Indentation level of current line

        Returns:
            Determined state or None if line is blank
        """
        if not line.strip():
            self.prev_line = line
            return None

        # Pass all required context to calculate_probabilities
        probs = self.calculate_probabilities(
            line=line,
            indentation=indentation,
            current_state=self.state,
            has_left_title=self.has_left_title,
            current_speaker=self.current_speaker,
            indent_context=self.indent_context,
            prev_line=self.prev_line,
            prev_non_empty_line=self.prev_non_empty_line,
        )

        # Update previous lines for next call
        self.prev_line = line
        self.prev_non_empty_line = line

        # Get the state with highest probability
        new_state = max(probs.items(), key=lambda x: x[1])[0]
        logger.debug(f"Determined state: {new_state} for line: {line.strip()[:40]}...")

        return new_state

    def is_page_number(self, line: str) -> bool:
        """
        Check if line is a page number.

        Args:
            line: Text line to check

        Returns:
            True if line appears to be a page number, False otherwise
        """
        stripped = line.strip()
        indentation = self.get_indentation(line)

        # Page numbers should be both numeric and highly indented
        is_page = (
            bool(re.match(r"^\s*\d+\.?\s*$", stripped))
            and indentation >= self.config.dialogue_indent_max + 5
        )

        if is_page:
            logger.debug(f"Detected page number: {stripped}")

        return is_page

    def get_indentation(self, line: str) -> int:
        """
        Get line indentation level.

        Args:
            line: Input line

        Returns:
            Number of leading whitespace characters
        """
        return len(line) - len(line.lstrip())

    def get_max_internal_spacing(self, line: str) -> int:
        """
        Get the maximum number of consecutive spaces in a line after stripping.

        Args:
            line: Input line to check

        Returns:
            Maximum number of consecutive spaces found
        """
        stripped = line.strip()
        if not stripped:
            return 0

        # Find all sequences of spaces and get the length of the longest one
        spaces = re.findall(r" +", stripped)
        return len(max(spaces, default=""))

    def is_dual_speaker(self, line: str, indentation: int) -> bool:
        """
        Check if a line appears to be a dual speaker attribution.

        Args:
            line: Text line to check
            indentation: Line indentation level

        Returns:
            True if line appears to be a dual speaker attribution, False otherwise
        """
        stripped = line.strip()
        return (
            stripped.isupper()
            and indentation < self.config.speaker_indent_min
            and self.config.get_dual_speaker_pattern().search(stripped) is not None
        )

    def is_scene_heading(self, line: str) -> bool:
        """
        Check if a line appears to be a scene heading.

        Args:
            line: Text line to check

        Returns:
            True if line appears to be a scene heading, False otherwise
        """
        stripped = line.strip()
        return self.config.get_scene_heading_pattern().match(stripped) is not None

    def is_speaker_attribution(self, line: str, indentation: int) -> bool:
        """
        Check if a line appears to be a speaker attribution.

        Args:
            line: Text line to check
            indentation: Line indentation level

        Returns:
            True if line appears to be a speaker attribution, False otherwise
        """
        stripped = line.strip()
        return (
            indentation >= self.config.speaker_indent_min
            and indentation <= self.config.speaker_indent_max
            and stripped.isupper()
            and not any(word in stripped.lower() for word in ["int.", "ext."])
        )

    def is_right_aligned_action(self, line: str, indentation: int) -> bool:
        """
        Check if a line appears to be a right-aligned action (like CUT TO:).

        Args:
            line: Text line to check
            indentation: Line indentation level

        Returns:
            True if line appears to be a right-aligned action, False otherwise
        """
        stripped = line.strip()
        return (
            indentation >= self.config.speaker_indent_max
            and stripped.isupper()
            and not any(word in stripped.lower() for word in ["int.", "ext."])
        )

    def is_dialogue_modifier(self, line: str) -> bool:
        """
        Check if a line appears to be a dialogue modifier (parenthetical).

        Args:
            line: Text line to check

        Returns:
            True if line appears to be a dialogue modifier, False otherwise
        """
        stripped = line.strip()
        return stripped.startswith("(") and (
            stripped.endswith(")") or len(stripped) > 1
        )

    def handle_state_transition(self, line: str, new_state: Optional[State]) -> None:
        """
        Handle transition between states.

        Args:
            line: Current line of text
            new_state: New determined state or None for blank lines
        """
        if new_state and new_state != State.TITLE:
            self.has_left_title = True

        if new_state is None:
            return

        # Update indentation context
        indentation = self.get_indentation(line)
        self.indent_context.update(new_state, indentation)

        if new_state != self.state or self.current_chunk is None:
            # Finish current chunk if there is one
            if self.current_chunk:
                self.chunks.append(self.current_chunk)
                logger.debug(f"Added chunk type: {self.current_chunk.type}")

            chunk_type = new_state.name.lower()
            speaker = None

            # Handle speaker transitions
            if new_state == State.SPEAKER_ATTRIBUTION:
                self.current_speaker = self.clean_speaker_name(line.strip())
                logger.debug(f"New speaker: {self.current_speaker}")
            elif new_state == State.DIALOGUE:
                speaker = self.current_speaker
            elif new_state in [State.DUAL_SPEAKER_ATTRIBUTION, State.DUAL_DIALOGUE]:
                # Reset speaker for dual dialogue sections
                self.current_speaker = ""
                speaker = None
            elif new_state == State.PAGE_NUMBER:
                # Special handling for page numbers
                logger.debug(f"Page number detected: {line.strip()}")

            # Create new chunk
            self.current_chunk = Chunk(
                type=chunk_type, speaker=speaker, raw_text=line, text=line.strip()
            )
        else:
            # Continue current chunk
            # Preserve exact formatting in raw_text
            self.current_chunk.raw_text += "\n" + line
            # Append cleaned text with space
            self.current_chunk.text += " " + line.strip()

        if new_state != self.state:
            logger.debug(f"State transition: {self.state} -> {new_state}")

        self.state = new_state

    def reset_parser_state(self) -> None:
        """
        Reset the parser state to initial values.
        """
        self.state = State.TITLE
        self.has_left_title = False
        self.current_speaker = ""
        self.current_chunk = None
        self.chunks = []
        self.indent_context = IndentationContext()
        self.prev_line = ""
        self.prev_non_empty_line = ""

    def _chunk_to_dict(self, chunk: Chunk) -> Dict[str, str]:
        """
        Convert a Chunk object to a dictionary.

        Args:
            chunk: Chunk object to convert

        Returns:
            Dictionary representation of the chunk
        """
        return {
            "type": chunk.type,
            "speaker": "" if chunk.speaker is None else chunk.speaker,
            "raw_text": chunk.raw_text,
            "text": chunk.text,
        }

    def process_line(self, line: str) -> List[Dict[str, str]]:
        """
        Process a single line of text and return any completed chunks.

        Args:
            line: A single line of text to process

        Returns:
            List of completed chunks (if any)
        """
        # Store current chunk before processing
        previous_chunk = self.current_chunk

        # Process the line
        indentation = self.get_indentation(line)
        new_state = self.determine_state(line, indentation)
        self.handle_state_transition(line, new_state)

        # Check if a new chunk was created (indicating previous chunk was completed)
        completed_chunks: List[Dict] = []
        if previous_chunk is not None and previous_chunk != self.current_chunk:
            # Convert to dict format
            completed_chunks.append(self._chunk_to_dict(previous_chunk))

        return completed_chunks

    def get_final_chunk(self) -> List[Dict[str, str]]:
        """
        Get the final chunk if processing is complete.

        This method returns at most one chunk (the current one) and resets
        the current_chunk to None.

        Returns:
            List containing the final chunk as a dictionary, or an empty list
        """
        final_chunks: List[Dict] = []

        # If there's a current chunk, add it to final chunks
        if self.current_chunk is not None:
            final_chunks.append(self._chunk_to_dict(self.current_chunk))
            self.current_chunk = None

        return final_chunks

    def parse_screenplay(self, text: str) -> List[Dict[str, str]]:
        """
        Parse screenplay using probabilistic state machine approach.

        Args:
            text: Full screenplay text

        Returns:
            List of parsed screenplay chunks
        """
        logger.info("Starting screenplay parsing")

        # Reset parser state
        self.reset_parser_state()

        lines = text.split("\n")
        i = 0

        while i < len(lines):
            line = lines[i]
            self.process_line(line)
            i += 1

        # Get any final chunk
        final_chunks = self.get_final_chunk()

        logger.info(
            f"Parsing completed. Generated {len(self.chunks) + len(final_chunks)} chunks"
        )

        # Combine all chunks
        all_chunks: List[Dict[str, str]] = [
            {
                "type": chunk.type,
                "speaker": "" if chunk.speaker is None else chunk.speaker,
                "raw_text": chunk.raw_text,
                "text": chunk.text,
            }
            for chunk in self.chunks
        ] + final_chunks

        return all_chunks
