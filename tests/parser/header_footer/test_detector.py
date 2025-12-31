"""Tests for HeaderFooterDetector."""

from unittest.mock import MagicMock, patch

import pytest

from script_to_speech.parser.constants import DEFAULT_LINES_TO_SCAN
from script_to_speech.parser.header_footer.detector import (
    DEFAULT_BLACKLIST,
    MIN_OCCURRENCES,
    MIN_PATTERN_LENGTH,
    HeaderFooterDetector,
)
from script_to_speech.parser.header_footer.models import PatternPosition
from script_to_speech.parser.utils.text_utils import PageText

# Use low min_occurrences for unit tests with small test data
TEST_MIN_OCCURRENCES = 2


@pytest.mark.unit
class TestHeaderFooterDetector:
    """Tests for HeaderFooterDetector class."""

    def test_init_with_defaults(self) -> None:
        """Test detector initializes with default values."""
        # Arrange & Act
        detector = HeaderFooterDetector()

        # Assert
        assert detector.lines_to_scan == DEFAULT_LINES_TO_SCAN
        assert detector.min_pattern_length == MIN_PATTERN_LENGTH
        assert detector.min_occurrences == MIN_OCCURRENCES
        assert detector.blacklist == DEFAULT_BLACKLIST

    def test_init_with_custom_values(self) -> None:
        """Test detector initializes with custom values."""
        # Arrange
        custom_blacklist = ["CUSTOM"]

        # Act
        detector = HeaderFooterDetector(
            lines_to_scan=3,
            min_pattern_length=10,
            min_occurrences=5,
            blacklist=custom_blacklist,
        )

        # Assert
        assert detector.lines_to_scan == 3
        assert detector.min_pattern_length == 10
        assert detector.min_occurrences == 5
        assert detector.blacklist == custom_blacklist

    @patch("script_to_speech.parser.header_footer.detector.extract_text_by_page")
    def test_detect_empty_pdf(self, mock_extract: MagicMock) -> None:
        """Test detection on empty PDF returns empty result."""
        # Arrange
        mock_extract.return_value = []
        detector = HeaderFooterDetector(min_occurrences=TEST_MIN_OCCURRENCES)

        # Act
        result = detector.detect("test.pdf")

        # Assert
        assert result.patterns == []
        assert result.total_pages == 0
        assert result.pdf_path == "test.pdf"

    @patch("script_to_speech.parser.header_footer.detector.extract_text_by_page")
    def test_detect_identical_headers(self, mock_extract: MagicMock) -> None:
        """Test detection of identical header text across pages."""
        # Arrange
        pages = [
            PageText(0, "SCRIPT TITLE\nContent line 1\nContent line 2"),
            PageText(1, "SCRIPT TITLE\nMore content\nEven more"),
            PageText(2, "SCRIPT TITLE\nFinal content\nThe end"),
        ]
        mock_extract.return_value = pages
        detector = HeaderFooterDetector(min_occurrences=TEST_MIN_OCCURRENCES)

        # Act
        result = detector.detect("test.pdf")

        # Assert
        assert result.total_pages == 3
        header_patterns = [
            p for p in result.patterns if p.position == PatternPosition.HEADER
        ]
        assert len(header_patterns) >= 1
        # Should find "SCRIPT TITLE" pattern
        titles = [p for p in header_patterns if "SCRIPT TITLE" in p.text]
        assert len(titles) >= 1
        assert titles[0].occurrence_count == 3
        assert titles[0].occurrence_percentage == 100.0

    @patch("script_to_speech.parser.header_footer.detector.extract_text_by_page")
    def test_detect_header_with_page_numbers(self, mock_extract: MagicMock) -> None:
        """Test detection finds common prefix when headers have varying page numbers."""
        # Arrange
        pages = [
            PageText(0, "SCRIPT TITLE - Rev 1.0          1.\nContent"),
            PageText(1, "SCRIPT TITLE - Rev 1.0          2.\nContent"),
            PageText(2, "SCRIPT TITLE - Rev 1.0          3.\nContent"),
        ]
        mock_extract.return_value = pages
        detector = HeaderFooterDetector(min_occurrences=TEST_MIN_OCCURRENCES)

        # Act
        result = detector.detect("test.pdf")

        # Assert
        header_patterns = [
            p for p in result.patterns if p.position == PatternPosition.HEADER
        ]
        # Should find "SCRIPT TITLE - Rev 1.0" as common prefix
        assert len(header_patterns) >= 1
        # The common prefix should be found
        common_prefix_found = any(
            "SCRIPT TITLE - Rev 1.0" in p.text for p in header_patterns
        )
        assert common_prefix_found

    @patch("script_to_speech.parser.header_footer.detector.extract_text_by_page")
    def test_detect_footer_patterns(self, mock_extract: MagicMock) -> None:
        """Test detection of footer patterns."""
        # Arrange
        pages = [
            PageText(0, "Content\nMore content\nFOOTER TEXT"),
            PageText(1, "Content\nMore content\nFOOTER TEXT"),
            PageText(2, "Content\nMore content\nFOOTER TEXT"),
        ]
        mock_extract.return_value = pages
        detector = HeaderFooterDetector(min_occurrences=TEST_MIN_OCCURRENCES)

        # Act
        result = detector.detect("test.pdf")

        # Assert
        footer_patterns = [
            p for p in result.patterns if p.position == PatternPosition.FOOTER
        ]
        assert len(footer_patterns) >= 1
        footers = [p for p in footer_patterns if "FOOTER TEXT" in p.text]
        assert len(footers) >= 1

    @patch("script_to_speech.parser.header_footer.detector.extract_text_by_page")
    def test_blacklist_patterns_flagged(self, mock_extract: MagicMock) -> None:
        """Test that blacklisted patterns are detected but flagged."""
        # Arrange
        pages = [
            PageText(0, "(CONTINUED)\nContent\nMore"),
            PageText(1, "(CONTINUED)\nContent\nMore"),
            PageText(2, "(CONTINUED)\nContent\nMore"),
        ]
        mock_extract.return_value = pages
        detector = HeaderFooterDetector(min_occurrences=TEST_MIN_OCCURRENCES)

        # Act
        result = detector.detect("test.pdf")

        # Assert
        blacklisted = [p for p in result.patterns if p.is_blacklisted]
        assert len(blacklisted) >= 1
        assert any("CONTINUED" in p.text for p in blacklisted)

    @patch("script_to_speech.parser.header_footer.detector.extract_text_by_page")
    def test_short_patterns_excluded(self, mock_extract: MagicMock) -> None:
        """Test that patterns shorter than min_pattern_length are excluded."""
        # Arrange
        pages = [
            PageText(0, "ABC\nContent content content"),
            PageText(1, "ABC\nContent content content"),
            PageText(2, "ABC\nContent content content"),
        ]
        mock_extract.return_value = pages
        detector = HeaderFooterDetector(min_pattern_length=5)

        # Act
        result = detector.detect("test.pdf")

        # Assert
        # "ABC" is only 3 chars, should not be detected
        short_patterns = [p for p in result.patterns if p.text == "ABC"]
        assert len(short_patterns) == 0

    @patch("script_to_speech.parser.header_footer.detector.extract_text_by_page")
    def test_blank_lines_excluded(self, mock_extract: MagicMock) -> None:
        """Test that blank lines are not considered as patterns."""
        # Arrange
        pages = [
            PageText(0, "\n\n\nActual content"),
            PageText(1, "\n\n\nActual content"),
            PageText(2, "\n\n\nActual content"),
        ]
        mock_extract.return_value = pages
        detector = HeaderFooterDetector(min_occurrences=TEST_MIN_OCCURRENCES)

        # Act
        result = detector.detect("test.pdf")

        # Assert
        # Should not have any empty/whitespace-only patterns
        for pattern in result.patterns:
            assert pattern.text.strip() != ""

    @patch("script_to_speech.parser.header_footer.detector.extract_text_by_page")
    def test_occurrence_percentage_calculation(self, mock_extract: MagicMock) -> None:
        """Test that occurrence percentage is calculated correctly."""
        # Arrange
        pages = [
            PageText(0, "HEADER\nContent"),
            PageText(1, "HEADER\nContent"),
            PageText(2, "Different\nContent"),
            PageText(3, "HEADER\nContent"),
        ]
        mock_extract.return_value = pages
        detector = HeaderFooterDetector(min_occurrences=TEST_MIN_OCCURRENCES)

        # Act
        result = detector.detect("test.pdf")

        # Assert
        header_patterns = [
            p
            for p in result.patterns
            if p.position == PatternPosition.HEADER and "HEADER" in p.text
        ]
        if header_patterns:
            pattern = header_patterns[0]
            assert pattern.occurrence_count == 3
            assert pattern.total_pages == 4
            assert pattern.occurrence_percentage == 75.0

    @patch("script_to_speech.parser.header_footer.detector.extract_text_by_page")
    def test_example_lines_included(self, mock_extract: MagicMock) -> None:
        """Test that example full lines are included in results."""
        # Arrange
        pages = [
            PageText(0, "TITLE - Page 1.\nContent"),
            PageText(1, "TITLE - Page 2.\nContent"),
            PageText(2, "TITLE - Page 3.\nContent"),
        ]
        mock_extract.return_value = pages
        detector = HeaderFooterDetector(min_occurrences=TEST_MIN_OCCURRENCES)

        # Act
        result = detector.detect("test.pdf")

        # Assert
        for pattern in result.patterns:
            if pattern.occurrence_count > 1:
                assert len(pattern.example_full_lines) > 0

    @patch("script_to_speech.parser.header_footer.detector.extract_text_by_page")
    def test_trailing_whitespace_merged(self, mock_extract: MagicMock) -> None:
        """Test that patterns with trailing whitespace differences are merged."""
        # Arrange - same header with different trailing whitespace
        pages = [
            PageText(0, "HEADER  1.\nContent"),  # "HEADER  " prefix (2 spaces)
            PageText(1, "HEADER  2.\nContent"),  # "HEADER  " prefix (2 spaces)
            PageText(2, "HEADER 3.\nContent"),  # "HEADER " prefix (1 space)
            PageText(3, "HEADER\nContent"),  # "HEADER" exact
        ]
        mock_extract.return_value = pages
        detector = HeaderFooterDetector(min_occurrences=TEST_MIN_OCCURRENCES)

        # Act
        result = detector.detect("test.pdf")

        # Assert - all should be merged into one "HEADER" pattern
        header_patterns = [
            p
            for p in result.patterns
            if p.position == PatternPosition.HEADER and p.text == "HEADER"
        ]
        assert len(header_patterns) == 1
        pattern = header_patterns[0]
        assert pattern.occurrence_count == 4  # All 4 pages
        assert pattern.occurrence_percentage == 100.0

    @patch("script_to_speech.parser.header_footer.detector.extract_text_by_page")
    def test_leading_whitespace_merged(self, mock_extract: MagicMock) -> None:
        """Test that patterns with leading whitespace differences are merged."""
        # Arrange - same header with different leading whitespace
        pages = [
            PageText(0, "   HEADER TEXT\nContent"),  # 3 leading spaces
            PageText(1, "  HEADER TEXT\nContent"),  # 2 leading spaces
            PageText(2, " HEADER TEXT\nContent"),  # 1 leading space
            PageText(3, "HEADER TEXT\nContent"),  # no leading space
        ]
        mock_extract.return_value = pages
        detector = HeaderFooterDetector(min_occurrences=TEST_MIN_OCCURRENCES)

        # Act
        result = detector.detect("test.pdf")

        # Assert - all should be merged into one "HEADER TEXT" pattern
        header_patterns = [
            p
            for p in result.patterns
            if p.position == PatternPosition.HEADER and p.text == "HEADER TEXT"
        ]
        assert len(header_patterns) == 1
        pattern = header_patterns[0]
        assert pattern.occurrence_count == 4
        assert pattern.occurrence_percentage == 100.0

    @patch("script_to_speech.parser.header_footer.detector.extract_text_by_page")
    def test_mixed_whitespace_variations_merged(self, mock_extract: MagicMock) -> None:
        """Test that patterns with both leading and trailing whitespace variations are merged."""
        # Arrange - header with page numbers and varying whitespace
        pages = [
            PageText(0, "   TITLE - Rev 1.0          1.\nContent"),
            PageText(1, "  TITLE - Rev 1.0         2.\nContent"),
            PageText(2, " TITLE - Rev 1.0        3.\nContent"),
            PageText(3, "TITLE - Rev 1.0       4.\nContent"),
        ]
        mock_extract.return_value = pages
        detector = HeaderFooterDetector(min_occurrences=TEST_MIN_OCCURRENCES)

        # Act
        result = detector.detect("test.pdf")

        # Assert - should find "TITLE - Rev 1.0" as the common pattern
        header_patterns = [
            p
            for p in result.patterns
            if p.position == PatternPosition.HEADER and "TITLE - Rev 1.0" in p.text
        ]
        assert len(header_patterns) >= 1
        # The pattern should cover all 4 pages
        pattern = header_patterns[0]
        assert pattern.occurrence_count == 4

    @patch("script_to_speech.parser.header_footer.detector.extract_text_by_page")
    def test_prefix_patterns_naturally_merged(self, mock_extract: MagicMock) -> None:
        """Test that prefix patterns are naturally merged by the LCP algorithm.

        When headers differ only by suffix (like page numbers), the LCP algorithm
        finds the common prefix and groups all occurrences together.
        """
        # Arrange - short pattern on some pages, longer pattern on others
        pages = [
            PageText(0, "CONCLAVE by Peter Straughan\nContent"),
            PageText(1, "CONCLAVE by Peter Straughan\nContent"),
            PageText(2, "CONCLAVE by Peter Straughan\nContent"),
            PageText(3, "CONCLAVE\nContent"),  # Only short version on this page
        ]
        mock_extract.return_value = pages
        detector = HeaderFooterDetector(min_occurrences=TEST_MIN_OCCURRENCES)

        # Act
        result = detector.detect("test.pdf")

        # Assert - the LCP algorithm finds "CONCLAVE" as common prefix across all pages
        # This is correct behavior - it groups them together
        header_patterns = [
            p for p in result.patterns if p.position == PatternPosition.HEADER
        ]
        conclave_patterns = [p for p in header_patterns if "CONCLAVE" in p.text]

        # All pages should be grouped under one pattern
        assert len(conclave_patterns) == 1
        assert conclave_patterns[0].occurrence_count == 4

    @patch("script_to_speech.parser.header_footer.detector.extract_text_by_page")
    def test_prefix_deduplication_keeps_non_prefixes(
        self, mock_extract: MagicMock
    ) -> None:
        """Test that non-prefix patterns are not deduplicated."""
        # Arrange - two different patterns that aren't prefixes of each other
        pages = [
            PageText(0, "HEADER ONE\nContent\nFOOTER TWO"),
            PageText(1, "HEADER ONE\nContent\nFOOTER TWO"),
            PageText(2, "HEADER ONE\nContent\nFOOTER TWO"),
        ]
        mock_extract.return_value = pages
        detector = HeaderFooterDetector(min_occurrences=TEST_MIN_OCCURRENCES)

        # Act
        result = detector.detect("test.pdf")

        # Assert - both patterns should remain since neither is a prefix of the other
        pattern_texts = [p.text for p in result.patterns]
        assert "HEADER ONE" in pattern_texts
        assert "FOOTER TWO" in pattern_texts


@pytest.mark.unit
class TestGetCandidateLines:
    """Tests for _get_candidate_lines method."""

    def test_get_first_n_non_blank_lines(self) -> None:
        """Test getting first N non-blank lines."""
        # Arrange
        detector = HeaderFooterDetector(lines_to_scan=3)
        lines = ["", "Line 1", "", "Line 2", "Line 3", "Line 4", "Line 5"]

        # Act
        result = detector._get_candidate_lines(lines, from_start=True)

        # Assert
        assert len(result) == 3
        assert result[0] == "Line 1"
        assert result[1] == "Line 2"
        assert result[2] == "Line 3"

    def test_get_last_n_non_blank_lines(self) -> None:
        """Test getting last N non-blank lines."""
        # Arrange
        detector = HeaderFooterDetector(lines_to_scan=3)
        lines = ["Line 1", "Line 2", "Line 3", "", "Line 4", "Line 5", ""]

        # Act
        result = detector._get_candidate_lines(lines, from_start=False)

        # Assert
        assert len(result) == 3
        assert result[0] == "Line 3"
        assert result[1] == "Line 4"
        assert result[2] == "Line 5"

    def test_fewer_lines_than_requested(self) -> None:
        """Test when there are fewer non-blank lines than requested."""
        # Arrange
        detector = HeaderFooterDetector(lines_to_scan=5)
        lines = ["Line 1", "", "Line 2"]

        # Act
        result = detector._get_candidate_lines(lines, from_start=True)

        # Assert
        assert len(result) == 2


@pytest.mark.unit
class TestFindCommonPrefix:
    """Tests for _find_common_prefix method."""

    def test_find_common_prefix_identical(self) -> None:
        """Test finding common prefix of identical strings."""
        # Arrange
        detector = HeaderFooterDetector(min_occurrences=TEST_MIN_OCCURRENCES)
        strings = ["HELLO WORLD", "HELLO WORLD", "HELLO WORLD"]

        # Act
        result = detector._find_common_prefix(strings)

        # Assert
        assert result == "HELLO WORLD"

    def test_find_common_prefix_varying_suffix(self) -> None:
        """Test finding common prefix with varying suffixes."""
        # Arrange
        detector = HeaderFooterDetector(min_occurrences=TEST_MIN_OCCURRENCES)
        strings = ["TITLE - Page 1", "TITLE - Page 2", "TITLE - Page 3"]

        # Act
        result = detector._find_common_prefix(strings)

        # Assert
        assert result == "TITLE - Page "

    def test_find_common_prefix_no_common(self) -> None:
        """Test when there is no common prefix."""
        # Arrange
        detector = HeaderFooterDetector(min_occurrences=TEST_MIN_OCCURRENCES)
        strings = ["ABC", "XYZ", "123"]

        # Act
        result = detector._find_common_prefix(strings)

        # Assert
        assert result == ""

    def test_find_common_prefix_empty_list(self) -> None:
        """Test with empty list."""
        # Arrange
        detector = HeaderFooterDetector(min_occurrences=TEST_MIN_OCCURRENCES)

        # Act
        result = detector._find_common_prefix([])

        # Assert
        assert result == ""

    def test_find_common_prefix_single_string(self) -> None:
        """Test with single string."""
        # Arrange
        detector = HeaderFooterDetector(min_occurrences=TEST_MIN_OCCURRENCES)

        # Act
        result = detector._find_common_prefix(["SINGLE"])

        # Assert
        assert result == "SINGLE"


@pytest.mark.unit
class TestIsBlacklisted:
    """Tests for _is_blacklisted method."""

    def test_exact_match_blacklisted(self) -> None:
        """Test exact match is blacklisted."""
        # Arrange
        detector = HeaderFooterDetector(min_occurrences=TEST_MIN_OCCURRENCES)

        # Act & Assert
        assert detector._is_blacklisted("CONTINUED") is True
        assert detector._is_blacklisted("(CONTINUED)") is True

    def test_case_insensitive_blacklist(self) -> None:
        """Test blacklist matching is case-insensitive."""
        # Arrange
        detector = HeaderFooterDetector(min_occurrences=TEST_MIN_OCCURRENCES)

        # Act & Assert
        assert detector._is_blacklisted("continued") is True
        assert detector._is_blacklisted("Continued") is True

    def test_prefix_match_blacklisted(self) -> None:
        """Test text starting with blacklist pattern is blacklisted."""
        # Arrange
        detector = HeaderFooterDetector(min_occurrences=TEST_MIN_OCCURRENCES)

        # Act & Assert
        assert detector._is_blacklisted("CONTINUED: (2)") is True

    def test_non_blacklisted(self) -> None:
        """Test non-blacklisted text."""
        # Arrange
        detector = HeaderFooterDetector(min_occurrences=TEST_MIN_OCCURRENCES)

        # Act & Assert
        assert detector._is_blacklisted("SCRIPT TITLE") is False
        assert detector._is_blacklisted("Random text") is False


@pytest.mark.unit
class TestExtractVariation:
    """Tests for _extract_variation method."""

    def test_extract_variation_with_double_space(self) -> None:
        """Test extracting variation when 2+ spaces separate content from page number."""
        # Arrange
        detector = HeaderFooterDetector(min_occurrences=TEST_MIN_OCCURRENCES)
        full_line = "HEADER - NOV 8    (4)"
        prefix = "HEADER - NOV"

        # Act
        result = detector._extract_variation(full_line, prefix)

        # Assert - should extract up to the double space
        assert result == "HEADER - NOV 8"

    def test_extract_variation_no_double_space(self) -> None:
        """Test when there's no 2+ whitespace - returns whole line."""
        # Arrange
        detector = HeaderFooterDetector(min_occurrences=TEST_MIN_OCCURRENCES)
        full_line = "HEADER - COMPLETE"
        prefix = "HEADER"

        # Act
        result = detector._extract_variation(full_line, prefix)

        # Assert - whole line returned since no 2+ whitespace
        assert result == "HEADER - COMPLETE"

    def test_extract_variation_prefix_mismatch(self) -> None:
        """Test when line doesn't start with prefix."""
        # Arrange
        detector = HeaderFooterDetector(min_occurrences=TEST_MIN_OCCURRENCES)
        full_line = "DIFFERENT HEADER"
        prefix = "HEADER"

        # Act
        result = detector._extract_variation(full_line, prefix)

        # Assert
        assert result is None

    def test_extract_variation_same_as_prefix(self) -> None:
        """Test when variation would be same as prefix."""
        # Arrange
        detector = HeaderFooterDetector(min_occurrences=TEST_MIN_OCCURRENCES)
        full_line = "HEADER    5."  # Double space right after prefix
        prefix = "HEADER"

        # Act
        result = detector._extract_variation(full_line, prefix)

        # Assert - should return None since variation == prefix after strip
        assert result is None

    def test_extract_variation_with_tabs(self) -> None:
        """Test that tabs count as whitespace."""
        # Arrange
        detector = HeaderFooterDetector(min_occurrences=TEST_MIN_OCCURRENCES)
        full_line = "TITLE - REV 1.0\t\t5."  # Tabs as separator
        prefix = "TITLE - REV"

        # Act
        result = detector._extract_variation(full_line, prefix)

        # Assert
        assert result == "TITLE - REV 1.0"


@pytest.mark.unit
class TestComputeVariations:
    """Tests for _compute_variations method."""

    @patch("script_to_speech.parser.header_footer.detector.extract_text_by_page")
    def test_compute_variations_frequent(self, mock_extract: MagicMock) -> None:
        """Test that frequent variations are captured."""
        # Arrange - same variation appears 4 times (>= MIN_VARIATION_OCCURRENCES)
        pages = [
            PageText(0, "HEADER - NOV 8    (1)\nContent"),
            PageText(1, "HEADER - NOV 8    (2)\nContent"),
            PageText(2, "HEADER - NOV 8    (3)\nContent"),
            PageText(3, "HEADER - NOV 8    (4)\nContent"),
            PageText(4, "HEADER - NOV 12    (5)\nContent"),
            PageText(5, "HEADER - NOV 12    (6)\nContent"),
            PageText(6, "HEADER - NOV 12    (7)\nContent"),
        ]
        mock_extract.return_value = pages
        detector = HeaderFooterDetector(min_occurrences=TEST_MIN_OCCURRENCES)

        # Act
        result = detector.detect("test.pdf")

        # Assert
        header_patterns = [
            p for p in result.patterns if p.position == PatternPosition.HEADER
        ]
        # Should find pattern with variations
        assert len(header_patterns) >= 1
        # Find the HEADER pattern
        header_pattern = next((p for p in header_patterns if "HEADER" in p.text), None)
        if header_pattern:
            # Both variations should be detected (each appears >= 3 times)
            assert "HEADER - NOV 8" in header_pattern.variations
            assert "HEADER - NOV 12" in header_pattern.variations

    @patch("script_to_speech.parser.header_footer.detector.extract_text_by_page")
    def test_compute_variations_infrequent_filtered(
        self, mock_extract: MagicMock
    ) -> None:
        """Test that infrequent variations are filtered out."""
        # Arrange - one variation appears only twice (< MIN_VARIATION_OCCURRENCES)
        pages = [
            PageText(0, "HEADER - NOV 8    (1)\nContent"),
            PageText(1, "HEADER - NOV 8    (2)\nContent"),
            PageText(2, "HEADER - NOV 8    (3)\nContent"),
            PageText(3, "HEADER - NOV 8    (4)\nContent"),
            PageText(4, "HEADER - NOV 99    (5)\nContent"),  # Only appears once
            PageText(5, "HEADER - NOV 99    (6)\nContent"),  # Only appears twice
        ]
        mock_extract.return_value = pages
        detector = HeaderFooterDetector(min_occurrences=TEST_MIN_OCCURRENCES)

        # Act
        result = detector.detect("test.pdf")

        # Assert
        header_patterns = [
            p for p in result.patterns if p.position == PatternPosition.HEADER
        ]
        if header_patterns:
            header_pattern = header_patterns[0]
            # NOV 8 appears 4 times - should be in variations
            assert "HEADER - NOV 8" in header_pattern.variations
            # NOV 99 appears only 2 times - should NOT be in variations
            assert "HEADER - NOV 99" not in header_pattern.variations
