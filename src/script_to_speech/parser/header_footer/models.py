"""Data models for header/footer detection."""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Set


class PatternPosition(Enum):
    """Position of detected pattern on page."""

    HEADER = "header"
    FOOTER = "footer"


@dataclass
class DetectedPattern:
    """Represents a detected header/footer pattern.

    Attributes:
        text: The common prefix/pattern string that can be removed
        position: Whether this is a header or footer pattern
        occurrence_count: Number of pages where this pattern was found
        total_pages: Total pages in the document
        occurrence_percentage: Percentage of pages where pattern appears (0-100)
        pages_found: Set of 0-indexed page numbers where pattern was found
        is_blacklisted: True if this pattern matches the blacklist
        example_full_lines: Sample of full lines containing this pattern (for context)
        variations: Frequent superstrings of the pattern (for --remove output)
    """

    text: str
    position: PatternPosition
    occurrence_count: int
    total_pages: int
    occurrence_percentage: float
    pages_found: Set[int] = field(default_factory=set)
    is_blacklisted: bool = False
    example_full_lines: List[str] = field(default_factory=list)
    variations: List[str] = field(default_factory=list)


@dataclass
class DetectionResult:
    """Complete result from header/footer detection.

    Attributes:
        patterns: All detected patterns (including blacklisted ones, flagged)
        pdf_path: Path to the source PDF file
        total_pages: Total pages in the document
        lines_scanned: Number of non-blank lines scanned per side (top/bottom)
        blacklist_applied: List of blacklist patterns that were checked
    """

    patterns: List[DetectedPattern]
    pdf_path: str
    total_pages: int
    lines_scanned: int
    blacklist_applied: List[str]
