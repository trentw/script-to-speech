"""Tests for header_footer data models."""

import pytest

from script_to_speech.parser.header_footer.models import (
    DetectedPattern,
    DetectionResult,
    PatternPosition,
)


@pytest.mark.unit
class TestPatternPosition:
    """Tests for PatternPosition enum."""

    def test_header_value(self) -> None:
        """Test HEADER has correct value."""
        assert PatternPosition.HEADER.value == "header"

    def test_footer_value(self) -> None:
        """Test FOOTER has correct value."""
        assert PatternPosition.FOOTER.value == "footer"


@pytest.mark.unit
class TestDetectedPattern:
    """Tests for DetectedPattern dataclass."""

    def test_create_basic_pattern(self) -> None:
        """Test creating a basic pattern."""
        # Arrange & Act
        pattern = DetectedPattern(
            text="TITLE",
            position=PatternPosition.HEADER,
            occurrence_count=10,
            total_pages=12,
            occurrence_percentage=83.33,
        )

        # Assert
        assert pattern.text == "TITLE"
        assert pattern.position == PatternPosition.HEADER
        assert pattern.occurrence_count == 10
        assert pattern.total_pages == 12
        assert pattern.occurrence_percentage == 83.33
        assert pattern.pages_found == set()  # Default
        assert pattern.is_blacklisted is False  # Default
        assert pattern.example_full_lines == []  # Default

    def test_create_pattern_with_all_fields(self) -> None:
        """Test creating a pattern with all fields specified."""
        # Arrange & Act
        pattern = DetectedPattern(
            text="CONTINUED",
            position=PatternPosition.FOOTER,
            occurrence_count=5,
            total_pages=10,
            occurrence_percentage=50.0,
            pages_found={0, 2, 4, 6, 8},
            is_blacklisted=True,
            example_full_lines=["CONTINUED", "(CONTINUED)"],
        )

        # Assert
        assert pattern.text == "CONTINUED"
        assert pattern.is_blacklisted is True
        assert pattern.pages_found == {0, 2, 4, 6, 8}
        assert len(pattern.example_full_lines) == 2


@pytest.mark.unit
class TestDetectionResult:
    """Tests for DetectionResult dataclass."""

    def test_create_empty_result(self) -> None:
        """Test creating an empty detection result."""
        # Arrange & Act
        result = DetectionResult(
            patterns=[],
            pdf_path="/path/to/test.pdf",
            total_pages=0,
            lines_scanned=5,
            blacklist_applied=["CONTINUED"],
        )

        # Assert
        assert result.patterns == []
        assert result.pdf_path == "/path/to/test.pdf"
        assert result.total_pages == 0
        assert result.lines_scanned == 5
        assert result.blacklist_applied == ["CONTINUED"]

    def test_create_result_with_patterns(self) -> None:
        """Test creating a result with patterns."""
        # Arrange
        pattern1 = DetectedPattern(
            text="HEADER",
            position=PatternPosition.HEADER,
            occurrence_count=10,
            total_pages=10,
            occurrence_percentage=100.0,
        )
        pattern2 = DetectedPattern(
            text="FOOTER",
            position=PatternPosition.FOOTER,
            occurrence_count=8,
            total_pages=10,
            occurrence_percentage=80.0,
        )

        # Act
        result = DetectionResult(
            patterns=[pattern1, pattern2],
            pdf_path="/path/to/script.pdf",
            total_pages=10,
            lines_scanned=5,
            blacklist_applied=["CONTINUED", "(MORE)"],
        )

        # Assert
        assert len(result.patterns) == 2
        assert result.patterns[0].text == "HEADER"
        assert result.patterns[1].text == "FOOTER"
