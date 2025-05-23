import re
from typing import Dict, List, Tuple

from ...utils.logging import get_screenplay_logger
from ..text_preprocessor_base import TextPreProcessor

logger = get_screenplay_logger(
    "text_processors.preprocessors.extract_dialogue_parentheticals"
)


class ExtractDialogueParentheticalsPreProcessor(TextPreProcessor):
    """
    Pre-processor that extracts parentheticals from dialogue chunks to create new chunks.

    For each dialogue chunk containing a parenthetical, creates:
    - dialogue chunk (text before parenthetical)
    - dialogue_modifier chunk (parenthetical content)
    - dialogue chunk (text after parenthetical)

    Processes recursively to handle multiple parentheticals in a single dialogue chunk.

    Config format:
    preprocessors:
      - name: extract_dialogue_parentheticals
        config:
          max_words: 10  # optional, maximum words in parenthetical
          extract_only:  # or extract_all_except
            - pause  # exact match, case insensitive, for (pause) / (PAUSE) / etc.
            - in irsh*  # asterisk for case insensitive, partial match, from start: (in Irish) (IN IRISH ACCENT), etc.
    """

    def validate_config(self) -> bool:
        """
        Validate the configuration for this pre-processor.

        Config schema:
        {
            "max_words": Optional[int],  # Maximum words in parenthetical to extract
            "extract_only": Optional[List[str]],  # List of patterns to extract
            "extract_all_except": Optional[List[str]]  # List of patterns to ignore
        }

        Returns:
            bool: True if configuration is valid
        """
        if not isinstance(self.config, dict):
            logger.error("Config must be a dictionary")
            return False

        # Validate max_words if present
        max_words = self.config.get("max_words")
        if max_words is not None and not (isinstance(max_words, int) and max_words > 0):
            logger.error("max_words must be a positive integer")
            return False

        # Validate extract_only and extract_all_except are mutually exclusive
        extract_only = self.config.get("extract_only", [])
        extract_all_except = self.config.get("extract_all_except", [])

        if extract_only and extract_all_except:
            logger.error("Cannot specify both extract_only and extract_all_except")
            return False

        # Validate pattern lists contain only strings
        for patterns in [extract_only, extract_all_except]:
            if not isinstance(patterns, list):
                logger.error("Pattern lists must be arrays")
                return False

            if not all(isinstance(p, str) for p in patterns):
                logger.error("All patterns must be strings")
                return False

        return True

    def _count_words(self, text: str) -> int:
        """Count words in text by splitting on whitespace."""
        return len(text.split())

    def _should_extract_parenthetical(self, parenthetical: str) -> bool:
        """
        Determine if a parenthetical should be extracted based on config rules.

        Args:
            parenthetical: The parenthetical text (without parentheses)

        Returns:
            bool: True if the parenthetical should be extracted
        """
        # Check max_words constraint
        max_words = self.config.get("max_words")
        if max_words and self._count_words(parenthetical) > max_words:
            return False

        # Clean parenthetical for matching
        parenthetical = parenthetical.strip().lower()

        # Handle extract_only patterns
        extract_only = self.config.get("extract_only", [])
        if extract_only:
            return any(
                self._matches_pattern(parenthetical, pattern)
                for pattern in extract_only
            )

        # Handle extract_all_except patterns
        extract_all_except = self.config.get("extract_all_except", [])
        if extract_all_except:
            return not any(
                self._matches_pattern(parenthetical, pattern)
                for pattern in extract_all_except
            )

        # If no patterns specified, extract all parentheticals
        return True

    def _matches_pattern(self, text: str, pattern: str) -> bool:
        """
        Check if text matches a pattern from config.

        Args:
            text: Text to check
            pattern: Pattern to match (with optional * suffix for partial matching)

        Returns:
            bool: True if text matches pattern
        """
        pattern = pattern.lower().strip()
        text = text.lower().strip()
        if pattern.endswith("*"):
            # Remove asterisk and check if text starts with pattern
            pattern = pattern[:-1]
            return text.startswith(pattern)
        return pattern in text

    def _split_dialogue_at_parenthetical(
        self, chunk: Dict, start_idx: int, end_idx: int, parenthetical: str
    ) -> List[Dict]:
        """
        Split a dialogue chunk at a parenthetical into multiple chunks.

        Args:
            chunk: Original dialogue chunk
            start_idx: Start index of parenthetical in text
            end_idx: End index of parenthetical in text
            parenthetical: The parenthetical text (with parentheses)

        Returns:
            List of new chunks (dialogue, dialogue_modifier, dialogue)
        """
        text = chunk["text"]
        before_text = text[:start_idx].strip()
        after_text = text[end_idx:].strip()
        result_chunks = []

        logger.debug("\nExtracting parenthetical: %s", parenthetical)
        logger.debug("Original text: %s", text)
        logger.debug("Speaker: %s", chunk["speaker"])

        # Add initial dialogue chunk if text exists before parenthetical
        if before_text:
            dialogue_before = {
                "type": "dialogue",
                "speaker": chunk["speaker"],
                "raw_text": chunk["raw_text"],
                "text": before_text,
            }
            result_chunks.append(dialogue_before)
            logger.debug("Created dialogue chunk (before): %s", before_text)

        # Add dialogue modifier (parenthetical)
        dialogue_mod = {
            "type": "dialogue_modifier",
            "speaker": "",
            "raw_text": chunk["raw_text"],
            "text": parenthetical,
        }
        result_chunks.append(dialogue_mod)
        logger.debug("Created dialogue modifier: %s", parenthetical)

        # Add final dialogue chunk if text exists after parenthetical
        if after_text:
            dialogue_after = {
                "type": "dialogue",
                "speaker": chunk["speaker"],
                "raw_text": chunk["raw_text"],
                "text": after_text,
            }
            result_chunks.append(dialogue_after)
            logger.debug("Created dialogue chunk (after): %s", after_text)

        return result_chunks

    def process(self, chunks: List[Dict]) -> Tuple[List[Dict], bool]:
        """
        Process chunks by extracting parentheticals from dialogue chunks.

        Args:
            chunks: List of all text chunks from the screenplay

        Returns:
            Tuple[List[Dict], bool]:
                - Modified list of chunks
                - Boolean indicating whether any changes were made
        """
        if not chunks:
            return chunks, False

        result_chunks = []
        made_changes = False
        i = 0

        while i < len(chunks):
            chunk = chunks[i]

            # Only process dialogue chunks
            if chunk["type"] != "dialogue":
                result_chunks.append(chunk)
                i += 1
                continue

            text = chunk["text"]
            # Look for a matching parenthetical in this chunk
            found_matching_parenthetical = False
            search_pos = 0

            while search_pos < len(text):
                # Find next parenthetical starting from current position
                match = re.search(r"\(([^)]+)\)", text[search_pos:])

                if not match:
                    break  # No more parentheticals

                # Adjust indices to account for the search offset
                actual_start = search_pos + match.start()
                actual_end = search_pos + match.end()
                parenthetical = match.group(
                    0
                )  # Full parenthetical text including parentheses
                parenthetical_content = match.group(1).strip()  # Just the content

                logger.info(
                    "Found dialogue parenthetical: %s (in dialogue: %s)",
                    parenthetical,
                    text,
                )

                if self._should_extract_parenthetical(parenthetical_content):
                    # We found a matching parenthetical - split at this point
                    found_matching_parenthetical = True

                    # Split chunk at parenthetical
                    new_chunks = self._split_dialogue_at_parenthetical(
                        chunk, actual_start, actual_end, parenthetical
                    )

                    made_changes = True
                    result_chunks.extend(
                        new_chunks[:-1]
                        if len(new_chunks) > 1 and new_chunks[-1]["type"] == "dialogue"
                        else new_chunks
                    )

                    # Continue processing from last dialogue chunk if it exists
                    last_dialogue = next(
                        (c for c in reversed(new_chunks) if c["type"] == "dialogue"),
                        None,
                    )
                    if last_dialogue and last_dialogue.get("text"):
                        # Insert the last dialogue chunk back for processing
                        chunks.insert(i + 1, last_dialogue)
                        logger.debug(
                            "Continuing processing with remaining dialogue: %s",
                            last_dialogue["text"],
                        )

                    break  # Exit the inner while loop to process the next chunk
                else:
                    logger.debug(
                        "Skipping parenthetical: %s (does not match extraction rules)",
                        parenthetical,
                    )
                    # Move search position past this parenthetical and continue looking
                    search_pos = actual_end

            # If we didn't find any matching parentheticals, keep the chunk as is
            if not found_matching_parenthetical:
                result_chunks.append(chunk)

            i += 1

        return result_chunks, made_changes
