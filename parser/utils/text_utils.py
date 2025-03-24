"""Text utility functions for the parser module."""


def extract_text_preserving_whitespace(pdf_path: str, output_file: str) -> str:
    """Extract text from PDF while preserving whitespace.

    Args:
        pdf_path: Path to the PDF file
        output_file: Path to save the extracted text

    Returns:
        Extracted text content
    """
    import pdfplumber
    from unidecode import unidecode

    with pdfplumber.open(pdf_path) as pdf:
        text = ""
        for page in pdf.pages:
            # Extract text with layout preservation
            page_text = page.dedupe_chars().extract_text(
                x_tolerance=1, y_tolerance=1, layout=True
            )
            # Convert to ASCII representation while preserving whitespace
            page_text = unidecode(page_text)
            text += page_text

    # Write the normalized text to the output file
    with open(output_file, "w", encoding="utf-8") as file:
        file.write(text)

    return text
