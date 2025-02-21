from typing import Dict, List, Tuple
import re
from ..text_preprocessor_base import TextPreProcessor
from utils.logging import get_screenplay_logger

logger = get_screenplay_logger(
    "text_processors.preprocessors.extract_dialog_parentheticals")


class ExtractDialogParentheticalsPreProcessor(TextPreProcessor):
    """
    Pre-processor that extracts parentheticals from dialog chunks to create new chunks.

    For each dialog chunk containing a parenthetical, creates:
    - dialog chunk (text before parenthetical)
    - dialog_modifier chunk (parenthetical content)
    - dialog chunk (text after parenthetical)

    Processes recursively to handle multiple parentheticals in a single dialog chunk.

    Config format:
    preprocessors:
      - name: extract_dialog_parentheticals
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
        max_words = self.config.get('max_words')
        if max_words is not None and not (isinstance(max_words, int) and max_words > 0):
            logger.error("max_words must be a positive integer")
            return False

        # Validate extract_only and extract_all_except are mutually exclusive
        extract_only = self.config.get('extract_only', [])
        extract_all_except = self.config.get('extract_all_except', [])

        if extract_only and extract_all_except:
            logger.error(
                "Cannot specify both extract_only and extract_all_except")
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
        max_words = self.config.get('max_words')
        if max_words and self._count_words(parenthetical) > max_words:
            return False

        # Clean parenthetical for matching
        parenthetical = parenthetical.strip().lower()

        # Handle extract_only patterns
        extract_only = self.config.get('extract_only', [])
        if extract_only:
            return any(self._matches_pattern(parenthetical, pattern)
                       for pattern in extract_only)

        # Handle extract_all_except patterns
        extract_all_except = self.config.get('extract_all_except', [])
        if extract_all_except:
            return not any(self._matches_pattern(parenthetical, pattern)
                           for pattern in extract_all_except)

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
        if pattern.endswith('*'):
            # Remove asterisk and check if text starts with pattern
            pattern = pattern[:-1]
            return text.startswith(pattern)
        return pattern in text

    def _split_dialog_at_parenthetical(
        self,
        chunk: Dict,
        start_idx: int,
        end_idx: int,
        parenthetical: str
    ) -> List[Dict]:
        """
        Split a dialog chunk at a parenthetical into multiple chunks.

        Args:
            chunk: Original dialog chunk
            start_idx: Start index of parenthetical in text
            end_idx: End index of parenthetical in text
            parenthetical: The parenthetical text (with parentheses)

        Returns:
            List of new chunks (dialog, dialog_modifier, dialog)
        """
        text = chunk['text']
        before_text = text[:start_idx].strip()
        after_text = text[end_idx:].strip()
        result_chunks = []

        logger.debug("\nExtracting parenthetical: %s", parenthetical)
        logger.debug("Original text: %s", text)
        logger.debug("Speaker: %s", chunk['speaker'])

        # Add initial dialog chunk if text exists before parenthetical
        if before_text:
            dialog_before = {
                'type': 'dialog',
                'speaker': chunk['speaker'],
                'raw_text': chunk['raw_text'],
                'text': before_text
            }
            result_chunks.append(dialog_before)
            logger.debug("Created dialog chunk (before): %s", before_text)

        # Add dialog modifier (parenthetical)
        dialog_mod = {
            'type': 'dialog_modifier',
            'speaker': '',
            'raw_text': chunk['raw_text'],
            'text': parenthetical
        }
        result_chunks.append(dialog_mod)
        logger.debug("Created dialog modifier: %s", parenthetical)

        # Add final dialog chunk if text exists after parenthetical
        if after_text:
            dialog_after = {
                'type': 'dialog',
                'speaker': chunk['speaker'],
                'raw_text': chunk['raw_text'],
                'text': after_text
            }
            result_chunks.append(dialog_after)
            logger.debug("Created dialog chunk (after): %s", after_text)

        return result_chunks

    def process(self, chunks: List[Dict]) -> Tuple[List[Dict], bool]:
        """
        Process chunks by extracting parentheticals from dialog chunks.

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

            # Only process dialog chunks
            if chunk['type'] != 'dialog':
                result_chunks.append(chunk)
                i += 1
                continue

            text = chunk['text']
            # Find first parenthetical
            match = re.search(r'\(([^)]+)\)', text)

            if not match:
                result_chunks.append(chunk)
                i += 1
                continue

            parenthetical = match.group(1).strip()
            logger.info("Found dialog parenthetical: %s (in dialog: %s)",
                        match.group(0), text)

            if not self._should_extract_parenthetical(parenthetical):
                logger.debug("Skipping parenthetical: %s (does not match extraction rules)",
                             match.group(0))
                result_chunks.append(chunk)
                i += 1
                continue

            # Split chunk at parenthetical
            new_chunks = self._split_dialog_at_parenthetical(
                chunk,
                match.start(),
                match.end(),
                match.group(0)
            )

            made_changes = True
            result_chunks.extend(new_chunks)

            # Continue processing from last dialog chunk if it exists
            last_dialog = next((c for c in reversed(new_chunks)
                                if c['type'] == 'dialog'), None)
            if last_dialog:
                # Replace last chunk with the one to process next
                result_chunks.pop()
                chunks.insert(i + 1, last_dialog)
                logger.debug("Continuing processing with remaining dialog: %s",
                             last_dialog['text'])

            i += 1

        return result_chunks, made_changes
