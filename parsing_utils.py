import pdfplumber
import json
import parsing3
from unidecode import unidecode


def pdf_to_output(pdf_path, text_file, json_file):
    text = extract_text_preserving_whitespace(pdf_path, text_file)
    json = parsing3.parse_screenplay(text)
    dump_to_file(json, json_file)


def read_text(input):
    with open(input, 'r') as file:
        # Read the contents of the file
        content = file.read()

        return content


def dump_to_file(input, output):
    with open(output, 'w') as file:
        file.write(json.dumps(input, indent=2, ensure_ascii=False))


def extract_text_preserving_whitespace(pdf_path: str, output_file: str) -> str:
    """
    Extract text from PDF while preserving whitespace and normalizing characters.
    Converts Unicode characters to their closest ASCII representation.

    Args:
        pdf_path: Path to input PDF file
        output_file: Path to output text file

    Returns:
        Extracted and normalized text
    """
    with pdfplumber.open(pdf_path) as pdf:
        text = ""
        for page in pdf.pages:
            # Extract text with layout preservation
            page_text = page.dedupe_chars().extract_text(
                x_tolerance=1,
                y_tolerance=1,
                layout=True
            )

            # Convert to ASCII representation while preserving whitespace
            page_text = unidecode(page_text)
            text += page_text

    # Write the normalized text to the output file
    with open(output_file, 'w', encoding='utf-8') as file:
        file.write(text)

    return text
