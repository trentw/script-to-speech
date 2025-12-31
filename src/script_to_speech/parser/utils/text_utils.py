"""Text utility functions for the parser module."""

from dataclasses import dataclass
from typing import List, Set, Tuple


@dataclass
class PageText:
    """Text content from a single PDF page.

    Attributes:
        page_number: 0-indexed page number
        text: Full text content of the page
    """

    page_number: int
    text: str


def extract_text_by_page(pdf_path: str) -> List[PageText]:
    """Extract text from PDF preserving page boundaries.

    Args:
        pdf_path: Path to the PDF file

    Returns:
        List of PageText objects, one per page
    """
    import pdfplumber
    from unidecode import unidecode

    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            # Extract text with layout preservation
            page_text = page.dedupe_chars().extract_text(
                x_tolerance=1, y_tolerance=1, layout=True
            )
            # Convert to ASCII representation while preserving whitespace
            page_text = unidecode(page_text) if page_text else ""
            pages.append(PageText(page_number=i, text=page_text))

    return pages


def extract_text_preserving_whitespace(pdf_path: str, output_file: str) -> str:
    """Extract text from PDF while preserving whitespace.

    Args:
        pdf_path: Path to the PDF file
        output_file: Path to save the extracted text

    Returns:
        Extracted text content
    """
    pages = extract_text_by_page(pdf_path)
    text = "".join(page.text for page in pages)

    # Write the normalized text to the output file
    with open(output_file, "w", encoding="utf-8") as file:
        file.write(text)

    return text


def get_header_footer_line_indices(
    lines: List[str],
    lines_to_scan: int,
) -> Tuple[Set[int], Set[int]]:
    """Get indices of first/last N non-blank lines.

    This utility identifies which line indices correspond to header (top)
    and footer (bottom) positions on a page, skipping blank lines.

    Args:
        lines: All lines from a page
        lines_to_scan: Number of non-blank lines to identify from each end

    Returns:
        Tuple of (header_indices, footer_indices) as sets of line indices
    """
    header_indices: Set[int] = set()
    count = 0
    for i, line in enumerate(lines):
        if line.strip():
            header_indices.add(i)
            count += 1
            if count >= lines_to_scan:
                break

    footer_indices: Set[int] = set()
    count = 0
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].strip():
            footer_indices.add(i)
            count += 1
            if count >= lines_to_scan:
                break

    return header_indices, footer_indices
