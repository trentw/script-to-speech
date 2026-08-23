"""Text utility functions for the parser module."""

import logging
from dataclasses import dataclass
from typing import List, Set, Tuple

logger = logging.getLogger(__name__)


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


@dataclass
class PageWord:
    """A single word with its bounding box on a PDF page.

    Coordinates are in PDF points with a top-left origin (pdfplumber's
    convention): `top` is the distance from the top of the page.

    Attributes:
        text: Word text, unidecoded to ASCII (matching extract_text_by_page)
        x0: Left edge
        x1: Right edge
        top: Top edge (distance from page top)
        bottom: Bottom edge
    """

    text: str
    x0: float
    x1: float
    top: float
    bottom: float


@dataclass
class PageWords:
    """Word boxes and dimensions for a single PDF page.

    Attributes:
        page_number: 0-indexed page number (matching PageText)
        width: Page width in PDF points
        height: Page height in PDF points
        words: Words in reading order (pdfplumber's positional sort)
        overlay_geometry_supported: Whether word coordinates use the same
            visible page box that pdf.js renders
    """

    page_number: int
    width: float
    height: float
    words: List["PageWord"]
    overlay_geometry_supported: bool = True


def extract_words_by_page(pdf_path: str) -> List[PageWords]:
    """Extract per-page word bounding boxes from a PDF.

    Uses the same character dedup and tolerances as extract_text_by_page so
    the word stream tokenizes consistently with the parse-time layout text.
    Purely additive companion to extract_text_by_page; parsing itself never
    uses word boxes.

    Args:
        pdf_path: Path to the PDF file

    Returns:
        List of PageWords objects, one per page
    """
    import pdfplumber
    from unidecode import unidecode

    pages = []
    cropbox_warned = False
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            # pdfplumber coordinates are MediaBox-relative, but PDF viewers
            # (pdf.js included) render the CropBox and normalize its origin.
            # A differing CropBox or a shifted page origin therefore needs an
            # explicit coordinate transform that we have not fixture-validated.
            # Flag it so the UI suppresses known-bad overlays instead of merely
            # logging a warning the user cannot see.
            cropbox = tuple(page.cropbox)
            mediabox = tuple(page.mediabox)
            overlay_geometry_supported = (
                cropbox == mediabox and cropbox[0] == 0 and cropbox[1] == 0
            )
            if not cropbox_warned and not overlay_geometry_supported:
                logger.warning(
                    f"PDF page {i} has unsupported visible geometry: "
                    f"CropBox {cropbox}, MediaBox {mediabox} in '{pdf_path}'; "
                    "viewer overlays derived from these word boxes may be offset"
                )
                cropbox_warned = True
            raw_words = page.dedupe_chars().extract_words(x_tolerance=1, y_tolerance=1)
            words = [
                PageWord(
                    text=unidecode(word["text"]),
                    x0=float(word["x0"]),
                    x1=float(word["x1"]),
                    top=float(word["top"]),
                    bottom=float(word["bottom"]),
                )
                for word in raw_words
            ]
            pages.append(
                PageWords(
                    page_number=i,
                    width=float(page.width),
                    height=float(page.height),
                    words=words,
                    overlay_geometry_supported=overlay_geometry_supported,
                )
            )

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
