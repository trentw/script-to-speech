"""CLI for header/footer detection in screenplay PDFs."""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..constants import DEFAULT_LINES_TO_SCAN
from .detector import (
    DEFAULT_BLACKLIST,
    MIN_OCCURRENCES,
    HeaderFooterDetector,
)
from .models import DetectedPattern, DetectionResult, PatternPosition

DEFAULT_OUTPUT_THRESHOLD = 30.0  # Default threshold for displaying patterns


def format_text_output(
    result: DetectionResult,
    include_blacklisted: bool,
    threshold: float = DEFAULT_OUTPUT_THRESHOLD,
) -> str:
    """Format detection results as human-readable text.

    Args:
        result: Detection result to format
        include_blacklisted: Whether to include blacklisted patterns in main output
        threshold: Minimum occurrence percentage to display (default 30%)

    Returns:
        Formatted text output
    """
    lines = []
    pdf_name = Path(result.pdf_path).name

    lines.append(f"Header/Footer Detection Results: {pdf_name}")
    lines.append("=" * (len(lines[0])))
    lines.append(f"Total pages: {result.total_pages}")
    lines.append(
        f"Lines scanned: {result.lines_scanned} (top) + {result.lines_scanned} (bottom) non-blank"
    )
    lines.append(f"Output threshold: {threshold:.0f}%")
    lines.append("")

    # Separate patterns by position and blacklist status
    headers = [p for p in result.patterns if p.position == PatternPosition.HEADER]
    footers = [p for p in result.patterns if p.position == PatternPosition.FOOTER]

    # Filter blacklisted unless requested
    if not include_blacklisted:
        headers_show = [p for p in headers if not p.is_blacklisted]
        footers_show = [p for p in footers if not p.is_blacklisted]
        headers_blacklisted = [p for p in headers if p.is_blacklisted]
        footers_blacklisted = [p for p in footers if p.is_blacklisted]
    else:
        headers_show = headers
        footers_show = footers
        headers_blacklisted = []
        footers_blacklisted = []

    # Apply threshold filter
    headers_show = [p for p in headers_show if p.occurrence_percentage >= threshold]
    footers_show = [p for p in footers_show if p.occurrence_percentage >= threshold]

    # Output headers
    lines.append("HEADERS (sorted by occurrence):")
    lines.append("-" * 35)
    if headers_show:
        for pattern in sorted(headers_show, key=lambda p: -p.occurrence_percentage):
            lines.append(_format_pattern(pattern))
    else:
        lines.append("  (none above threshold)")
    lines.append("")

    # Output footers
    lines.append("FOOTERS (sorted by occurrence):")
    lines.append("-" * 35)
    if footers_show:
        for pattern in sorted(footers_show, key=lambda p: -p.occurrence_percentage):
            lines.append(_format_pattern(pattern))
    else:
        lines.append("  (none above threshold)")
    lines.append("")

    # Output blacklisted patterns separately (not threshold-filtered)
    all_blacklisted = headers_blacklisted + footers_blacklisted
    if all_blacklisted:
        lines.append("BLACKLISTED (not shown by default, use --include-blacklisted):")
        lines.append("-" * 60)
        for pattern in sorted(all_blacklisted, key=lambda p: -p.occurrence_percentage):
            pct = f"{pattern.occurrence_percentage:.1f}%"
            lines.append(
                f'[{pct}] "{pattern.text}" - found on {pattern.occurrence_count}/{pattern.total_pages} pages'
            )
        lines.append("")

    # Generate copy-paste --remove string
    all_patterns_above_threshold = sorted(
        headers_show + footers_show,
        key=lambda p: -p.occurrence_percentage,
    )
    # Deduplicate by text (headers and footers may have same text)
    seen_texts: set = set()
    unique_patterns: List[DetectedPattern] = []
    for p in all_patterns_above_threshold:
        if p.text not in seen_texts:
            seen_texts.add(p.text)
            unique_patterns.append(p)

    if unique_patterns:
        lines.append("Copy-paste for sts-parse-screenplay:")
        lines.append("-" * 40)

        # Collect all remove strings, preferring variations when available
        remove_strings: List[str] = []
        for p in unique_patterns:
            if p.variations:
                # Use variations instead of the truncated prefix
                remove_strings.extend(p.variations)
            else:
                remove_strings.append(p.text)

        # Deduplicate remove strings while preserving order
        seen_removes: set = set()
        unique_removes: List[str] = []
        for s in remove_strings:
            if s not in seen_removes:
                seen_removes.add(s)
                unique_removes.append(s)

        remove_args = " ".join(f"--remove '{s}'" for s in unique_removes)
        lines.append(remove_args)
        lines.append("")

    return "\n".join(lines)


def _format_pattern(pattern: DetectedPattern) -> str:
    """Format a single pattern for text output.

    Args:
        pattern: Pattern to format

    Returns:
        Formatted string
    """
    lines = []
    pct = f"{pattern.occurrence_percentage:.1f}%"
    blacklist_note = " [BLACKLISTED]" if pattern.is_blacklisted else ""

    lines.append(f'[{pct}] "{pattern.text}"{blacklist_note}')
    lines.append(
        f"        Found on {pattern.occurrence_count}/{pattern.total_pages} pages"
    )

    # Show variations if found
    if pattern.variations:
        lines.append(f"        Variations ({len(pattern.variations)}):")
        for var in pattern.variations[:5]:  # Show up to 5 variations
            # Truncate long variations
            display_var = var if len(var) <= 60 else var[:57] + "..."
            lines.append(f'          - "{display_var}"')
        if len(pattern.variations) > 5:
            lines.append(f"          ... and {len(pattern.variations) - 5} more")
    elif pattern.example_full_lines:
        # Fall back to example if no variations
        example = pattern.example_full_lines[0]
        if example.strip() != pattern.text:
            # Truncate long examples
            if len(example) > 80:
                example = example[:77] + "..."
            lines.append(f'        Example: "{example.strip()}"')

    return "\n".join(lines)


def format_json_output(
    result: DetectionResult,
    include_blacklisted: bool,
    threshold: float = DEFAULT_OUTPUT_THRESHOLD,
) -> str:
    """Format detection results as JSON.

    Args:
        result: Detection result to format
        include_blacklisted: Whether to include blacklisted patterns
        threshold: Minimum occurrence percentage to include (default 30%)

    Returns:
        JSON string
    """
    patterns_data: List[Dict[str, Any]] = []

    for pattern in result.patterns:
        if not include_blacklisted and pattern.is_blacklisted:
            continue
        if pattern.occurrence_percentage < threshold:
            continue

        patterns_data.append(
            {
                "text": pattern.text,
                "position": pattern.position.value,
                "occurrence_count": pattern.occurrence_count,
                "total_pages": pattern.total_pages,
                "occurrence_percentage": round(pattern.occurrence_percentage, 2),
                "pages_found": sorted(pattern.pages_found),
                "is_blacklisted": pattern.is_blacklisted,
                "example_full_lines": pattern.example_full_lines,
                "variations": pattern.variations,
            }
        )

    output = {
        "pdf_path": result.pdf_path,
        "total_pages": result.total_pages,
        "lines_scanned": result.lines_scanned,
        "threshold_percent": threshold,
        "blacklist_applied": result.blacklist_applied,
        "patterns": patterns_data,
    }

    return json.dumps(output, indent=2)


def main() -> None:
    """CLI entry point for header/footer detection."""
    parser = argparse.ArgumentParser(
        description="Detect recurring header/footer patterns in screenplay PDFs. "
        "Outputs patterns that can be removed during screenplay parsing.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  sts-detect-headers screenplay.pdf
  sts-detect-headers screenplay.pdf --json
  sts-detect-headers screenplay.pdf --lines 3
  sts-detect-headers screenplay.pdf --include-blacklisted

The output shows patterns found in the first/last N lines of each page,
with their occurrence percentage. Use these strings with the --remove
option of sts-parse-screenplay to clean headers/footers before parsing.
""",
    )

    parser.add_argument(
        "pdf_file",
        help="Path to the PDF file to analyze",
    )

    parser.add_argument(
        "--lines",
        type=int,
        default=DEFAULT_LINES_TO_SCAN,
        metavar="N",
        help=f"Number of non-blank lines to scan from top/bottom of each page (default: {DEFAULT_LINES_TO_SCAN})",
    )

    parser.add_argument(
        "--min-occurrences",
        type=int,
        default=MIN_OCCURRENCES,
        metavar="N",
        help=f"Minimum page occurrences to report a pattern (default: {MIN_OCCURRENCES})",
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON instead of human-readable text",
    )

    parser.add_argument(
        "--include-blacklisted",
        action="store_true",
        help="Include blacklisted patterns (like 'CONTINUED') in the main output",
    )

    parser.add_argument(
        "--no-blacklist",
        action="store_true",
        help="Disable the default blacklist entirely",
    )

    parser.add_argument(
        "--threshold",
        type=float,
        default=DEFAULT_OUTPUT_THRESHOLD,
        metavar="PCT",
        help=f"Minimum occurrence percentage to display (default: {DEFAULT_OUTPUT_THRESHOLD:.0f}%%)",
    )

    args = parser.parse_args()

    # Validate input file
    pdf_path = Path(args.pdf_file)
    if not pdf_path.exists():
        print(f"Error: File not found: {args.pdf_file}", file=sys.stderr)
        sys.exit(1)

    if pdf_path.suffix.lower() != ".pdf":
        print(f"Error: File must be a PDF: {args.pdf_file}", file=sys.stderr)
        sys.exit(1)

    # Create detector
    blacklist: Optional[List[str]] = (
        [] if args.no_blacklist else None
    )  # None means use default
    detector = HeaderFooterDetector(
        lines_to_scan=args.lines,
        min_occurrences=args.min_occurrences,
        blacklist=blacklist,
    )

    # Run detection
    try:
        result = detector.detect(str(pdf_path))
    except Exception as e:
        print(f"Error processing PDF: {e}", file=sys.stderr)
        sys.exit(1)

    # Format and output
    if args.json:
        output = format_json_output(result, args.include_blacklisted, args.threshold)
    else:
        output = format_text_output(result, args.include_blacklisted, args.threshold)

    print(output)


if __name__ == "__main__":
    main()
