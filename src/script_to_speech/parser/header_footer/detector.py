"""Header/footer pattern detection for screenplay PDFs."""

import re
from collections import defaultdict
from typing import Dict, List, Optional, Set, Tuple

from ..constants import DEFAULT_LINES_TO_SCAN
from ..utils.text_utils import (
    PageText,
    extract_text_by_page,
    get_header_footer_line_indices,
)
from .models import DetectedPattern, DetectionResult, PatternPosition

# Default blacklist - patterns that appear in screenplays but should NOT be removed
DEFAULT_BLACKLIST = [
    "CONTINUED",
    "(CONTINUED)",
    "CONTINUED:",
    "CONTINUED: (2)",
    "CONTINUED: (3)",
    "CONTINUED: (4)",
    "(MORE)",
]

MIN_PATTERN_LENGTH = 5
MIN_OCCURRENCES = 10  # Default minimum page occurrences for a pattern
MAX_EXAMPLE_LINES = 3  # Maximum number of example lines to include
MIN_VARIATION_OCCURRENCES = 3  # Minimum occurrences for a variation to be reported


class HeaderFooterDetector:
    """Detects recurring header/footer patterns in screenplay PDFs.

    This detector analyzes the first and last N non-blank lines of each page
    to find patterns that repeat across multiple pages. It uses longest common
    prefix matching to handle cases where headers include varying page numbers.

    Attributes:
        lines_to_scan: Number of non-blank lines to scan from top/bottom of each page
        min_pattern_length: Minimum character length for a valid pattern
        min_occurrences: Minimum page occurrences required for a pattern
        blacklist: List of patterns to flag as blacklisted (e.g., "CONTINUED")
    """

    def __init__(
        self,
        lines_to_scan: int = DEFAULT_LINES_TO_SCAN,
        min_pattern_length: int = MIN_PATTERN_LENGTH,
        min_occurrences: int = MIN_OCCURRENCES,
        blacklist: Optional[List[str]] = None,
    ):
        """Initialize the detector.

        Args:
            lines_to_scan: Number of non-blank lines to scan from top/bottom
            min_pattern_length: Minimum pattern length to report
            min_occurrences: Minimum page occurrences to report a pattern (default 10)
            blacklist: Patterns to mark as blacklisted (uses DEFAULT_BLACKLIST if None)
        """
        self.lines_to_scan = lines_to_scan
        self.min_pattern_length = min_pattern_length
        self.min_occurrences = min_occurrences
        self.blacklist = (
            blacklist if blacklist is not None else DEFAULT_BLACKLIST.copy()
        )

    def detect(self, pdf_path: str) -> DetectionResult:
        """Detect header/footer patterns in a PDF.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            DetectionResult containing all detected patterns
        """
        # Extract text page-by-page
        pages = extract_text_by_page(pdf_path)
        total_pages = len(pages)

        if total_pages == 0:
            return DetectionResult(
                patterns=[],
                pdf_path=pdf_path,
                total_pages=0,
                lines_scanned=self.lines_to_scan,
                blacklist_applied=self.blacklist,
            )

        # Collect candidate lines into pools
        header_pool: List[Tuple[str, int]] = []  # (line_text, page_number)
        footer_pool: List[Tuple[str, int]] = []

        for page in pages:
            lines = page.text.split("\n")

            # Get header candidates (first N non-blank lines)
            header_lines = self._get_candidate_lines(lines, from_start=True)
            for line in header_lines:
                header_pool.append((line, page.page_number))

            # Get footer candidates (last N non-blank lines)
            footer_lines = self._get_candidate_lines(lines, from_start=False)
            for line in footer_lines:
                footer_pool.append((line, page.page_number))

        # Find patterns in each pool
        header_patterns = self._find_patterns(
            header_pool, PatternPosition.HEADER, total_pages
        )
        footer_patterns = self._find_patterns(
            footer_pool, PatternPosition.FOOTER, total_pages
        )

        # Combine and sort patterns
        all_patterns = header_patterns + footer_patterns
        all_patterns.sort(key=lambda p: (-p.occurrence_percentage, -len(p.text)))

        return DetectionResult(
            patterns=all_patterns,
            pdf_path=pdf_path,
            total_pages=total_pages,
            lines_scanned=self.lines_to_scan,
            blacklist_applied=self.blacklist,
        )

    def _get_candidate_lines(self, lines: List[str], from_start: bool) -> List[str]:
        """Get first or last N non-blank lines.

        Args:
            lines: All lines from a page
            from_start: If True, get from start; if False, get from end

        Returns:
            List of non-blank lines (stripped but preserving internal whitespace)
        """
        header_indices, footer_indices = get_header_footer_line_indices(
            lines, self.lines_to_scan
        )
        indices = header_indices if from_start else footer_indices
        # Return lines at those indices, preserving order
        return [lines[i] for i in sorted(indices)]

    def _find_patterns(
        self,
        pool: List[Tuple[str, int]],
        position: PatternPosition,
        total_pages: int,
    ) -> List[DetectedPattern]:
        """Find patterns in a pool of lines.

        Groups lines by common prefix and returns patterns that meet
        the minimum length requirement. Patterns are merged by their
        trimmed text to ensure whitespace variations don't split counts.

        Args:
            pool: List of (line_text, page_number) tuples
            position: Whether this is a header or footer pool
            total_pages: Total pages in the document

        Returns:
            List of detected patterns
        """
        if not pool:
            return []

        # Group lines by common prefix
        prefix_groups = self._group_by_prefix(pool)

        # First pass: merge groups by trimmed prefix
        # This ensures "HEADER  " and "HEADER" count as the same pattern
        merged_patterns: Dict[str, Tuple[Set[int], List[str], bool]] = {}

        for prefix, (page_set, example_lines) in prefix_groups.items():
            # Skip patterns that are too short
            if len(prefix) < self.min_pattern_length:
                continue

            # Strip whitespace from prefix (both leading and trailing)
            trimmed_prefix = prefix.strip()

            # Skip if trimmed prefix is too short
            if len(trimmed_prefix) < self.min_pattern_length:
                continue

            # Check if blacklisted
            is_blacklisted = self._is_blacklisted(trimmed_prefix)

            if trimmed_prefix in merged_patterns:
                # Merge with existing pattern
                existing_pages, existing_examples, existing_blacklisted = (
                    merged_patterns[trimmed_prefix]
                )
                merged_pages = existing_pages | page_set
                # Add new examples that aren't duplicates
                merged_examples = existing_examples + [
                    ex for ex in example_lines if ex not in existing_examples
                ]
                merged_patterns[trimmed_prefix] = (
                    merged_pages,
                    merged_examples[:MAX_EXAMPLE_LINES],
                    existing_blacklisted or is_blacklisted,
                )
            else:
                merged_patterns[trimmed_prefix] = (
                    page_set,
                    example_lines[:MAX_EXAMPLE_LINES],
                    is_blacklisted,
                )

        # Second pass: create DetectedPattern objects with accurate counts
        # Filter out patterns below minimum occurrence threshold
        patterns = []
        for trimmed_prefix, (
            page_set,
            example_lines,
            is_blacklisted,
        ) in merged_patterns.items():
            occurrence_count = len(page_set)

            # Skip patterns below minimum occurrences
            if occurrence_count < self.min_occurrences:
                continue

            occurrence_pct = (occurrence_count / total_pages) * 100

            patterns.append(
                DetectedPattern(
                    text=trimmed_prefix,
                    position=position,
                    occurrence_count=occurrence_count,
                    total_pages=total_pages,
                    occurrence_percentage=occurrence_pct,
                    pages_found=page_set,
                    is_blacklisted=is_blacklisted,
                    example_full_lines=example_lines,
                )
            )

        # Compute variations for each pattern (before deduplication)
        for pattern in patterns:
            pattern.variations = self._compute_variations(pattern, pool)

        # Third pass: deduplicate prefix patterns
        # If pattern A is a prefix of pattern B and both meet min_occurrences,
        # only keep the longer pattern B (removing B will also remove A)
        final_patterns: List[DetectedPattern] = []
        patterns_sorted = sorted(patterns, key=lambda p: -len(p.text))  # longest first

        for pattern in patterns_sorted:
            # Check if this pattern is a prefix of any already-kept pattern
            is_prefix_of_longer = False
            for kept in final_patterns:
                if kept.text.startswith(pattern.text) and kept.text != pattern.text:
                    is_prefix_of_longer = True
                    break

            if not is_prefix_of_longer:
                final_patterns.append(pattern)

        return final_patterns

    def _group_by_prefix(
        self, pool: List[Tuple[str, int]]
    ) -> Dict[str, Tuple[Set[int], List[str]]]:
        """Group lines by their common prefix.

        Uses a greedy approach: sorts lines lexicographically, then
        iterates through finding groups that share a common prefix.

        Args:
            pool: List of (line_text, page_number) tuples

        Returns:
            Dict mapping prefix -> (set of page numbers, list of example lines)
        """
        if not pool:
            return {}

        # Find prefix groups using lexicographic sorting
        result = self._find_prefix_groups(pool)

        # Collect and merge exact matches
        exact_matches = self._collect_exact_matches(pool)
        self._merge_exact_matches_into_result(exact_matches, result)

        return result

    def _find_prefix_groups(
        self, pool: List[Tuple[str, int]]
    ) -> Dict[str, Tuple[Set[int], List[str]]]:
        """Find groups of lines sharing a common prefix using lexicographic sorting.

        Args:
            pool: List of (line_text, page_number) tuples

        Returns:
            Dict mapping prefix -> (set of page numbers, list of example lines)
        """
        sorted_pool = sorted(pool, key=lambda x: x[0])
        result: Dict[str, Tuple[Set[int], List[str]]] = {}

        i = 0
        while i < len(sorted_pool):
            current_line, current_page = sorted_pool[i]
            current_stripped = current_line.strip()

            if not current_stripped:
                i += 1
                continue

            # Find best prefix group starting from this line
            best_prefix, best_pages, best_examples, next_i = (
                self._find_prefix_group_from(
                    sorted_pool, i, current_stripped, current_line, current_page
                )
            )

            # Add to result if it meets criteria
            if len(best_pages) > 1 or len(best_prefix) >= self.min_pattern_length:
                self._add_prefix_to_result(
                    result, best_prefix, best_pages, best_examples
                )

            i = next_i

        return result

    def _find_prefix_group_from(
        self,
        sorted_pool: List[Tuple[str, int]],
        start_idx: int,
        current_stripped: str,
        current_line: str,
        current_page: int,
    ) -> Tuple[str, Set[int], List[str], int]:
        """Find a prefix group starting from a given index.

        Args:
            sorted_pool: Lexicographically sorted pool
            start_idx: Starting index in pool
            current_stripped: Stripped text of current line
            current_line: Original line text
            current_page: Page number of current line

        Returns:
            Tuple of (best_prefix, pages_set, example_lines, next_index)
        """
        best_prefix = current_stripped
        best_pages: Set[int] = {current_page}
        best_examples: List[str] = [current_line]

        j = start_idx + 1
        while j < len(sorted_pool):
            next_line, next_page = sorted_pool[j]
            next_stripped = next_line.strip()

            if not next_stripped:
                j += 1
                continue

            common = self._find_common_prefix([best_prefix, next_stripped])

            if len(common) >= self.min_pattern_length:
                best_prefix = common
                best_pages.add(next_page)
                if next_line not in best_examples:
                    best_examples.append(next_line)
                j += 1
            else:
                break

        next_i = j if j > start_idx + 1 else start_idx + 1
        return best_prefix, best_pages, best_examples, next_i

    def _add_prefix_to_result(
        self,
        result: Dict[str, Tuple[Set[int], List[str]]],
        prefix: str,
        pages: Set[int],
        examples: List[str],
    ) -> None:
        """Add a prefix to result, handling subsumption with existing prefixes.

        Args:
            result: Result dict to modify
            prefix: New prefix to potentially add
            pages: Pages where prefix was found
            examples: Example lines for this prefix
        """
        should_add = True
        for existing_prefix in list(result.keys()):
            existing_pages, _ = result[existing_prefix]
            # If existing prefix contains this one and covers same/more pages
            if existing_prefix.startswith(prefix) and existing_pages >= pages:
                should_add = False
                break
            # If this prefix contains existing one, replace if more pages
            if prefix.startswith(existing_prefix) and pages >= existing_pages:
                del result[existing_prefix]

        if should_add:
            result[prefix] = (pages, examples)

    def _collect_exact_matches(
        self, pool: List[Tuple[str, int]]
    ) -> Dict[str, Tuple[Set[int], List[str]]]:
        """Collect lines that appear identically across pages.

        Args:
            pool: List of (line_text, page_number) tuples

        Returns:
            Dict mapping exact text -> (set of page numbers, list of example lines)
        """
        exact_matches: Dict[str, Tuple[Set[int], List[str]]] = defaultdict(
            lambda: (set(), [])
        )
        for line, page in pool:
            stripped = line.strip()
            if len(stripped) >= self.min_pattern_length:
                pages, examples = exact_matches[stripped]
                pages.add(page)
                if line not in examples and len(examples) < MAX_EXAMPLE_LINES:
                    examples.append(line)
                exact_matches[stripped] = (pages, examples)
        return dict(exact_matches)

    def _merge_exact_matches_into_result(
        self,
        exact_matches: Dict[str, Tuple[Set[int], List[str]]],
        result: Dict[str, Tuple[Set[int], List[str]]],
    ) -> None:
        """Merge exact matches with prefix groups in result.

        Args:
            exact_matches: Dict of exact text matches
            result: Result dict to modify in place
        """
        for exact_text, (exact_pages, exact_examples) in exact_matches.items():
            subsuming_prefix = self._find_subsuming_prefix(exact_text, result)

            if subsuming_prefix is not None:
                # Merge pages into existing prefix group
                existing_pages, existing_examples = result[subsuming_prefix]
                merged_pages = existing_pages | exact_pages
                merged_examples = existing_examples + [
                    ex for ex in exact_examples if ex not in existing_examples
                ]
                result[subsuming_prefix] = (
                    merged_pages,
                    merged_examples[:MAX_EXAMPLE_LINES],
                )
            elif len(exact_pages) > 1:
                # Only add non-subsumed patterns if they appear on multiple pages
                result[exact_text] = (exact_pages, exact_examples)

    def _find_subsuming_prefix(
        self,
        text: str,
        result: Dict[str, Tuple[Set[int], List[str]]],
    ) -> Optional[str]:
        """Find an existing prefix that subsumes the given text.

        Args:
            text: Text to check
            result: Dict of existing prefix groups

        Returns:
            Subsuming prefix if found, None otherwise
        """
        text_stripped = text.strip()
        for prefix in result.keys():
            if text_stripped.startswith(prefix.strip()):
                return prefix
        return None

    def _find_common_prefix(self, strings: List[str]) -> str:
        """Find the longest common prefix among a list of strings.

        Args:
            strings: List of strings to compare

        Returns:
            The longest common prefix, or empty string if none
        """
        if not strings:
            return ""

        if len(strings) == 1:
            return strings[0]

        # Start with the first string as the prefix
        prefix = strings[0]

        for s in strings[1:]:
            # Shorten prefix until it matches
            while not s.startswith(prefix) and prefix:
                prefix = prefix[:-1]

            if not prefix:
                break

        return prefix

    def _is_blacklisted(self, text: str) -> bool:
        """Check if text matches any blacklist pattern.

        The check is case-insensitive and matches if the text
        contains or equals any blacklist pattern.

        Args:
            text: Text to check

        Returns:
            True if text matches blacklist
        """
        text_upper = text.strip().upper()
        for pattern in self.blacklist:
            pattern_upper = pattern.upper()
            # Exact match or text starts/ends with pattern
            if text_upper == pattern_upper or text_upper.startswith(pattern_upper):
                return True
        return False

    def _extract_variation(self, full_line: str, prefix: str) -> Optional[str]:
        """Extract the portion of full_line up to 2+ whitespace chars after prefix.

        This is used to find "superstrings" of a common prefix that end before
        page numbers (which are typically separated by multiple spaces).

        Example:
            full_line: "HEADER - NOV 8    (4)"
            prefix: "HEADER - NOV"
            Returns: "HEADER - NOV 8"

        Args:
            full_line: The complete line text
            prefix: The common prefix to extend from

        Returns:
            The variation string, or None if line doesn't start with prefix
        """
        stripped_line = full_line.strip()
        if not stripped_line.startswith(prefix):
            return None

        # Find where 2+ whitespace chars occur after the prefix
        remainder = stripped_line[len(prefix) :]

        # Use regex to find first occurrence of 2+ whitespace
        match = re.search(r"\s{2,}", remainder)
        if match:
            # Return prefix + content up to the whitespace
            variation = (prefix + remainder[: match.start()]).strip()
            # Return None if variation equals prefix (no new content)
            return variation if variation and variation != prefix else None
        else:
            # No 2+ whitespace found, return the whole stripped line
            return stripped_line if stripped_line != prefix else None

    def _compute_variations(
        self, pattern: DetectedPattern, pool: List[Tuple[str, int]]
    ) -> List[str]:
        """Compute frequent variations of a pattern from the pool.

        Args:
            pattern: The detected pattern with common prefix
            pool: Full pool of (line_text, page_number) tuples

        Returns:
            List of variation strings that occur frequently
        """
        variation_counts: Dict[str, int] = defaultdict(int)

        # Count variations from ALL lines in pool that match this prefix
        for line, page in pool:
            stripped = line.strip()
            if stripped.startswith(pattern.text):
                variation = self._extract_variation(stripped, pattern.text)
                if variation and variation != pattern.text:
                    variation_counts[variation] += 1

        # Keep variations that occur frequently
        return sorted(
            [
                v
                for v, count in variation_counts.items()
                if count >= MIN_VARIATION_OCCURRENCES
            ],
            key=lambda v: -variation_counts[v],  # Sort by frequency descending
        )
